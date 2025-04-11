import base64
import io
import logging
import os
import httpx # 导入 httpx
import PIL.Image

logger = logging.getLogger(__name__)

# 从环境变量读取图床配置
CF_IMGBED_UPLOAD_URL = os.getenv("CF_IMGBED_UPLOAD_URL")
CF_IMGBED_API_KEY = os.getenv("CF_IMGBED_API_KEY")

# --- Local Save Path Configuration (Always attempt to read) ---
OUTPUT_IMAGE_PATH = os.getenv("OUTPUT_IMAGE_PATH") # Read from environment
DEFAULT_LOCAL_PATH = os.path.expanduser("~/gen_image") # Define default path

if OUTPUT_IMAGE_PATH:
    logger.info(f"Local save path configured: {OUTPUT_IMAGE_PATH}")
    # Ensure the directory exists
    if not os.path.exists(OUTPUT_IMAGE_PATH):
        try:
            os.makedirs(OUTPUT_IMAGE_PATH)
            logger.info(f"Created local save directory: {OUTPUT_IMAGE_PATH}")
        except OSError as e:
            logger.error(f"Failed to create local save directory {OUTPUT_IMAGE_PATH}: {e}. Local saving might fail.")
            OUTPUT_IMAGE_PATH = None # Disable local saving if directory creation fails
else:
    # Optionally, decide if you want to use a default path if the env var is not set
    # If you want a default path uncomment the following lines:
    # logger.warning(f"OUTPUT_IMAGE_PATH environment variable not set. Using default local path: {DEFAULT_LOCAL_PATH}")
    # OUTPUT_IMAGE_PATH = DEFAULT_LOCAL_PATH
    # if not os.path.exists(OUTPUT_IMAGE_PATH):
    #     try:
    #         os.makedirs(OUTPUT_IMAGE_PATH)
    #         logger.info(f"Created default local save directory: {DEFAULT_LOCAL_PATH}")
    #     except OSError as e:
    #         logger.error(f"Failed to create default local save directory {DEFAULT_LOCAL_PATH}: {e}. Disabling local saving.")
    #         OUTPUT_IMAGE_PATH = None # Disable if default creation fails
    # else: # If you DON'T want a default path, keep OUTPUT_IMAGE_PATH as None
        logger.info("OUTPUT_IMAGE_PATH not configured. Local saving is disabled.")
        OUTPUT_IMAGE_PATH = None # Explicitly set to None if not configured

# --- Log ImgBed Configuration Status ---
if CF_IMGBED_UPLOAD_URL and CF_IMGBED_API_KEY:
    logger.info("CloudFlare-ImgBed configured. Will attempt to upload.")
else:
    logger.warning("CloudFlare-ImgBed URL or API Key not configured. Upload to ImgBed is disabled.")


def validate_base64_image(base64_string: str) -> bool:
    """Validate if a string is a valid base64-encoded image.

    Args:
        base64_string: The base64 string to validate

    Returns:
        True if valid, False otherwise
    """
    try:
        # Try to decode base64
        image_data = base64.b64decode(base64_string)

        # Try to open as image
        with PIL.Image.open(io.BytesIO(image_data)) as img:
            logger.debug(
                f"Validated base64 image, format: {img.format}, size: {img.size}"
            )
            return True

    except Exception as e:
        logger.warning(f"Invalid base64 image: {str(e)}")
        return False
    
async def upload_to_cf_imgbed(image_data: bytes, filename: str) -> str:
    """Upload image data to CloudFlare-ImgBed and return the public URL.

    Args:
        image_data: Raw image data (bytes).
        filename: The desired filename for the uploaded image (e.g., "my_image.png").

    Returns:
        The public URL of the uploaded image.

    Raises:
        ValueError: If ImgBed URL or API Key is not configured.
        httpx.HTTPStatusError: If the upload request fails.
        Exception: For other potential errors during upload.
    """
    if not CF_IMGBED_UPLOAD_URL or not CF_IMGBED_API_KEY:
        raise ValueError("CloudFlare-ImgBed URL or API Key not configured in environment variables.")

    # Check if the base URL already contains query parameters
    separator = '&' if '?' in CF_IMGBED_UPLOAD_URL else '?'
    upload_url_with_auth = f"{CF_IMGBED_UPLOAD_URL}{separator}authCode={CF_IMGBED_API_KEY}"

    files = {'file': (filename, image_data, 'image/png')} # Assume PNG, adjust if needed

    async with httpx.AsyncClient() as client:
        try:
            logger.info(f"Uploading image '{filename}' to {CF_IMGBED_UPLOAD_URL}...")
            response = await client.post(upload_url_with_auth, files=files, timeout=60.0) # Increased timeout
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            response_data = response.json()
            logger.debug(f"ImgBed Response: {response_data}")

            if isinstance(response_data, list) and len(response_data) > 0 and 'src' in response_data[0]:
                image_path_segment = response_data[0]['src']
                # Construct the full URL based on the upload URL's origin
                # Manually construct the base URL from scheme and host for robustness
                parsed_upload_url = httpx.URL(CF_IMGBED_UPLOAD_URL)
                base_url_str = f"{parsed_upload_url.scheme}://{parsed_upload_url.host}"
                # Use httpx.URL again to correctly join the base and the path segment
                full_url = str(httpx.URL(base_url_str).join(image_path_segment))
                logger.info(f"Image uploaded successfully: {full_url}")
                return full_url
            else:
                logger.error(f"Unexpected response format from ImgBed: {response_data}")
                raise ValueError("Could not extract image URL from ImgBed response.")

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error uploading to ImgBed: {e.response.status_code} - {e.response.text}")
            raise
        except Exception as e:
            logger.error(f"Error uploading image to ImgBed: {str(e)}")
            raise


async def _save_locally(image_data: bytes, filename_with_ext: str) -> str:
    """Helper function to save image data locally."""
    if not OUTPUT_IMAGE_PATH:
         raise ValueError("Local save requested but OUTPUT_IMAGE_PATH is not configured.")
    try:
        # Open image from bytes
        image = PIL.Image.open(io.BytesIO(image_data))
        # Save the image locally
        local_image_path = os.path.join(OUTPUT_IMAGE_PATH, filename_with_ext)
        image.save(local_image_path)
        logger.info(f"Image saved locally to {local_image_path}")
        return local_image_path
    except Exception as e:
        logger.error(f"Error saving image locally: {str(e)}")
        raise

async def save_or_upload_image(image_data: bytes, filename_base: str) -> str:
    """Save image locally or upload to CloudFlare-ImgBed based on configuration.
       If upload succeeds, also attempts to save locally if configured.

    Args:
        image_data: Raw image data (bytes).
        filename_base: Base string for the filename (without extension).

    Returns:
        The public URL of the uploaded image if upload succeeds.
        The local path to the saved image file if upload fails (fallback) or if ImgBed is not configured.
    """
    filename_with_ext = f"{filename_base}.png" # Assume PNG for now

    if CF_IMGBED_UPLOAD_URL and CF_IMGBED_API_KEY:
        # Attempt to upload to ImgBed first
        try:
            uploaded_url = await upload_to_cf_imgbed(image_data, filename_with_ext)
            logger.info(f"Successfully uploaded to ImgBed: {uploaded_url}")

            # --- Also save locally if upload succeeded and local path is configured ---
            if OUTPUT_IMAGE_PATH:
                try:
                    await _save_locally(image_data, filename_with_ext)
                    logger.info("Also saved a local copy.")
                except Exception as local_save_error:
                    # Log warning but don't fail the overall operation if only local save fails
                    logger.warning(f"ImgBed upload succeeded, but saving local copy failed: {local_save_error}")
            # --- End local save attempt ---

            return uploaded_url # Return the uploaded URL as the primary result

        except Exception as upload_error:
            logger.error(f"ImgBed upload failed: {upload_error}. Checking for local fallback.")
            # Fallback to local save ONLY if configured
            if OUTPUT_IMAGE_PATH:
                logger.warning("Falling back to local save.")
                # Proceed to local save logic below
                pass # Let execution continue to the local save block
            else:
                # No fallback possible, re-raise the original upload error
                logger.error("No local save path configured. Upload error cannot be recovered.")
                raise upload_error
    else:
         logger.info("ImgBed not configured. Proceeding with local save if configured.")
         # Proceed to local save logic below

    # --- Local Save Logic (Primary if ImgBed not configured, or Fallback if upload failed) ---
    if OUTPUT_IMAGE_PATH:
         # This block is reached if ImgBed is not configured OR if upload failed and fallback is enabled
         return await _save_locally(image_data, filename_with_ext)
    else:
         # This case is reached if ImgBed wasn't configured AND local wasn't configured,
         # OR if upload failed and local fallback wasn't configured (error already raised above).
         # Primarily handles the case where no storage option is configured at all.
         raise ValueError("Image saving failed: Neither ImgBed nor local OUTPUT_IMAGE_PATH is configured or available.")
