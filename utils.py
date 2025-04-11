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

# 只有在未配置图床时才使用本地路径
OUTPUT_IMAGE_PATH = None
if not CF_IMGBED_UPLOAD_URL or not CF_IMGBED_API_KEY:
    OUTPUT_IMAGE_PATH = os.getenv("OUTPUT_IMAGE_PATH") or os.path.expanduser("~/gen_image")
    if not os.path.exists(OUTPUT_IMAGE_PATH):
        os.makedirs(OUTPUT_IMAGE_PATH)
    logger.warning("CloudFlare-ImgBed URL or API Key not configured. Images will be saved locally.")
else:
    logger.info("CloudFlare-ImgBed configured. Images will be uploaded to the image bed.")

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
                base_url = httpx.URL(CF_IMGBED_UPLOAD_URL).origin
                full_url = str(base_url.join(image_path_segment))
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


async def save_or_upload_image(image_data: bytes, filename_base: str) -> str:
    """Save image locally or upload to CloudFlare-ImgBed based on configuration.

    Args:
        image_data: Raw image data (bytes).
        filename_base: Base string for the filename (without extension).

    Returns:
        If ImgBed is configured: The public URL of the uploaded image.
        Otherwise: The local path to the saved image file.
    """
    filename_with_ext = f"{filename_base}.png" # Assume PNG for now

    if CF_IMGBED_UPLOAD_URL and CF_IMGBED_API_KEY:
        # Upload to ImgBed
        try:
            return await upload_to_cf_imgbed(image_data, filename_with_ext)
        except Exception as upload_error:
            logger.error(f"ImgBed upload failed: {upload_error}. Falling back to local save.")
            # Fallback to local save if upload fails and local path is configured
            if OUTPUT_IMAGE_PATH:
                pass # Proceed to local save logic below
            else:
                raise upload_error # Re-raise if no local fallback is possible
    
    # --- Local Save Logic (Fallback or if ImgBed not configured) ---
    if not OUTPUT_IMAGE_PATH:
         raise ValueError("Image saving/upload failed: Neither ImgBed nor local OUTPUT_IMAGE_PATH is configured.")

    try:
        # Open image from bytes
        image = PIL.Image.open(io.BytesIO(image_data))

        # Save the image locally
        local_image_path = os.path.join(OUTPUT_IMAGE_PATH, filename_with_ext)
        image.save(local_image_path)
        logger.info(f"Image saved locally to {local_image_path}")

        # Displaying the image is usually not needed in a server context.
        # image.show()

        return local_image_path # Return local path as fallback/default
    except Exception as e:
        logger.error(f"Error saving image locally: {str(e)}")
        raise
