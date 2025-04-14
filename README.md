# Gemini Image Generator MCP Server

Generate high-quality images from text prompts using Google's Gemini model via the Model Context Protocol (MCP).

## Overview & Features

This MCP server enables AI assistants to generate and transform images using Google's Gemini AI models. It handles prompt engineering, text-to-image/image-to-image conversion, intelligent filename generation, optional image uploading (e.g., to CloudFlare-ImgBed), and local image storage.

**Key Features:**

*   Text-to-image generation using Gemini models.
*   Image-to-image transformation based on text prompts.
*   Supports transforming local image files.
*   Automatic intelligent filename generation based on prompts.
*   Automatic translation of non-English prompts to English for better results.
*   Local image storage with configurable output path (`OUTPUT_IMAGE_PATH`).
*   Optional image uploading to a configured CloudFlare-ImgBed service.
*   High-resolution image output.
*   Returns image URLs (if uploaded) or local file paths.
*   Tool to list recently generated images.

## Available MCP Tools

The server provides the following MCP tools:

1.  **`generate_image_from_text`**
    *   **Description**: Generates a new image based on the provided text prompt using Google's Gemini model.
    *   **Signature**: `generate_image_from_text(prompt: str) -> str`
    *   **Parameters**:
        *   `prompt` (str): User's text prompt describing the desired image. English prompts are recommended for best results.
    *   **Returns**: (str) The public URL of the generated image (if uploaded) or the filename of the locally saved image. Returns an error message string on failure.
    *   **Example Usage**: "Generate an image of a cat riding a bicycle on the moon."

2.  **`list_generated_images`**
    *   **Description**: Lists image files stored in the configured `OUTPUT_IMAGE_PATH`. Useful for finding filenames to use with `transform_image_from_file`.
    *   **Signature**: `list_generated_images(limit: Optional[int] = None) -> Union[List[str], str]`
    *   **Parameters**:
        *   `limit` (Optional[int]): Maximum number of image paths to return (between 10 and 100). If None, returns all found images. Defaults to None.
    *   **Returns**: (Union[List[str], str]) A list of full paths to the image files found (sorted by modification time, newest first, up to the limit), or an error message string.
    *   **Example Usage**: "List the last 10 generated images."

3.  **`transform_image_from_file`**
    *   **Description**: Transforms an existing image file based on its filename and a text prompt using Google's Gemini model.
    *   **Important**: Use `list_generated_images` first to get the exact filename of the image you want to modify.
    *   **Signature**: `transform_image_from_file(image_filename: str, prompt: str) -> str`
    *   **Parameters**:
        *   `image_filename` (str): Exact filename of the image to transform (e.g., "cat_on_moon_bike_abc123.png"). Get this from `list_generated_images`.
        *   `prompt` (str): Text prompt describing the desired transformation. English prompts are recommended.
    *   **Returns**: (str) The public URL of the transformed image (if uploaded) or the filename of the locally saved transformed image. Returns an error message string on failure.
    *   **Example Usage**: (After getting filename 'cat_on_moon_bike_abc123.png' from `list_generated_images`) "Transform 'cat_on_moon_bike_abc123.png' by adding stars in the background."

### Known Issues (Claude Desktop Host)

When using this MCP server with Claude Desktop Host:

1.  **Path Resolution Problems**: There may be issues with correctly resolving image paths returned by the server, especially if only local paths are returned (i.e., no image uploading service is configured). The host application might not properly interpret the returned file paths, making it difficult to access the generated images directly through the host interface. Using an image uploading service (like ImgBed) is recommended for easier access via URLs.

## Setup

### Prerequisites

*   Python 3.11+
*   Google AI API key (Gemini)
*   MCP host application (e.g., Claude Desktop App, Cursor, or other MCP-compatible clients)
*   Optional: ImgBed service details if you want image uploading.

### Getting a Gemini API Key

1.  Visit the [Google AI Studio API Keys page](https://aistudio.google.com/apikey).
2.  Sign in with your Google account.
3.  Click "Create API Key".
4.  Copy your new API key.
5.  Note: The API key provides a certain quota of free usage. Check your usage in the Google AI Studio.

### Installation

1.  Clone the repository:
    ```bash
    git clone https://github.com/slot181/gemini-image-generator-mcp.git # Replace with actual URL if different
    cd gemini-image-generator-mcp
    ```

2.  Create a virtual environment and install dependencies:
    ```bash
    # Using standard venv
    python -m venv .venv
    source .venv/bin/activate  # On Windows use `.venv\Scripts\activate`
    pip install -e .

    # Or using uv (recommended)
    uv venv
    source .venv/bin/activate # On Windows use `.venv\Scripts\activate`
    uv pip install -e .
    ```

3.  Configure environment variables:
    Copy `.env.example` to `.env`:
    ```bash
    cp .env.example .env
    ```
    Edit the `.env` file and add your details:
    ```env
    GEMINI_API_KEY="your-gemini-api-key-here"
    OUTPUT_IMAGE_PATH="/path/to/save/images" # IMPORTANT: Use an absolute path

    # Optional: CloudFlare-ImgBed Configuration (uncomment and fill if using)
    # CF_IMGBED_UPLOAD_URL="your_imgbed_api_url"
    # CF_IMGBED_API_KEY="your_imgbed_api_token"
    ```
    *   Ensure `OUTPUT_IMAGE_PATH` exists and the server has write permissions.

### Configure MCP Client (Example: Claude Desktop)

Add the server configuration to your MCP client's settings file (e.g., `claude_desktop_config.json`):

*   **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
*   **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`
*   **Linux**: `~/.config/Claude/claude_desktop_config.json`

```json
{
    "mcpServers": {
        "gemini-image-generator": {
            "command": "uv",
            "args": [
                "--directory",
                "/absolute/path/to/gemini-image-generator",
                "run",
                "server.py"
            ],
            "env": {
                "GEMINI_API_KEY": "GEMINI_API_KEY",
                "OUTPUT_IMAGE_PATH": "OUTPUT_IMAGE_PATH",
                "CF_IMGBED_UPLOAD_URL": "https://your-imgbed.pages.dev/upload", // Optional
                "CF_IMGBED_API_KEY": "CF_IMGBED_API_KEY" // Optional
            }
        }
    }
}
```
*   **Crucially**, replace `/absolute/path/to/gemini-image-generator-mcp` with the actual absolute path to the project directory on your system.
*   Adjust the `command` and `args` based on how you installed dependencies (uv or standard venv/pip).

## Usage

Once installed and configured:

1.  **Generate Images**: Ask your MCP client (e.g., Claude) to generate an image:
    *   "Generate an image of a futuristic city at sunset."
    *   "Create a picture of a dog wearing a chef's hat."

2.  **List Images**: To see what's available for transformation:
    *   "List the generated images."
    *   "Show me the last 15 images created."
    The tool will return a list of image file paths. Note the exact filename you want to modify.

3.  **Transform Images**: Use the filename from the list:
    *   "Transform the image named 'futuristic_sunset_city_xyz789.png' by adding flying cars."
    *   "Edit 'dog_chef_hat_abc123.png' to make the background a kitchen."

The server will save the images to your `OUTPUT_IMAGE_PATH` and return the URL (if uploaded) or the new filename.

## License

MIT License
