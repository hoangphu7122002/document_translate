import os
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from src.utils.utils import *
from src.app_config import app_context
from werkzeug.utils import secure_filename
from pydantic import BaseModel
from typing import List

# Set CUDA environment variables
os.environ["CUDA_DEVICE_ORDER"] = "PCI_BUS_ID"
os.environ["CUDA_VISIBLE_DEVICES"] = "4"

# Initialize FastAPI app
app = FastAPI(
    title="vOffice Translate",
    description="API for vOffice document translation",
    version="1.0"
)

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
    allow_credentials=True,
)

# File upload directory
home_dir = os.getcwd()
UPLOAD_FOLDER = os.path.join(home_dir, "data/upload")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# Initialize translation pipeline
translate_pipeline = None

async def save_file(file, folder_path:str):
    """
    Save a file received from a request to the specified folder path.

    Params:
        file: The file object received from the request form.
        folder_path (str): The path to the folder where the file will be saved on the server.

    Returns:
        str or None: The path where the file was saved if successful, None otherwise.

    Note:
        If the content type of the file is not 'application/pdf', logs a warning message
        indicating the failure to save the file due to an incorrect file format.
    """
    file_name = secure_filename(file.filename)

    # create folder if not exists
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    
    # save file
    save_path = os.path.join(folder_path, file_name)

    if file.content_type != 'application/pdf':
        print(f"Failed to save file {file_name}: {file_name[-4:]} instead of .pdf")
        #log.warning_log(f"Failed to save file {file_name}: {file_name[-4:]} instead of .pdf")
        return None
    
    try:
        with open(save_path, "wb") as buffer:
            buffer.write(await file.read())  # Read and write the file content
        return save_path
        # file.save(save_path)
        # return save_path

    except Exception as e:
        print(f"Failed to save file {file_name}: {e}")
        # log.warning_log(f"Failed to save file {file_name}: {e}")
        return None

# Status route
@app.get("/translate-docs/status")
def status():
    return JSONResponse(content={"status": "OK"})


# Endpoint to process PDF file from Vietnamese to English
@app.post("/translate-docs/process-file-vi2en")
async def process_file_vi2en(file: UploadFile):
    # Save file
    file_name = secure_filename(file.filename).lower()
    save_path = await save_file(file, UPLOAD_FOLDER)
    
    # Validate PDF
    is_valid = pdf_validation(save_path)
    if not is_valid:
        raise HTTPException(status_code=415, detail="File error")

    # Process PDF file
    try:
        translate = translate_pipeline.process(path=save_path, en_vi=False)
    except Exception:
        translate = translate_pipeline.raw_process_file(path=save_path, en_vi=False)

    # Return translation response
    return JSONResponse(content={"bot_response": translate})


# Endpoint to process PDF file from English to Vietnamese
@app.post("/translate-docs/process-file-en2vi")
async def process_file_en2vi(file: UploadFile):
    # Save file
    file_name = secure_filename(file.filename).lower()
    save_path = await save_file(file, UPLOAD_FOLDER)
    
    # Validate PDF
    is_valid = pdf_validation(save_path)
    if not is_valid:
        raise HTTPException(status_code=415, detail="File error")

    # Process PDF file
    try:
        translate = translate_pipeline.process(path=save_path, en_vi=True)
    except Exception:
        translate = translate_pipeline.raw_process_file(path=save_path, en_vi=True)

    # Return translation response
    return JSONResponse(content={"bot_response": translate})

class DocsRequest(BaseModel):
    docs: List[str]

# Endpoint to process raw documents from Vietnamese to English
@app.post("/translate-docs/process-raw-docs-vi2en")
async def process_raw_docs_vi2en(request: DocsRequest):
    try:
        # docs_content = docs["docs"]
        docs_content = request.docs
    except KeyError:
        return JSONResponse(content={"bot_response": "Không dịch được với thông tin đã cung cấp!!"})

    translate = translate_pipeline.raw_process(docs=docs_content, en_vi=False)
    return JSONResponse(content={"bot_response": translate})


# Endpoint to process raw documents from English to Vietnamese
@app.post("/translate-docs/process-raw-docs-en2vi")
async def process_raw_docs_en2vi(request: DocsRequest):
    try:
        # docs_content = docs["docs"]
        docs_content = request.docs
    except KeyError:
        return JSONResponse(content={"bot_response": "Không dịch được với thông tin đã cung cấp!!"})

    translate = translate_pipeline.raw_process(docs=docs_content, en_vi=True)
    return JSONResponse(content={"bot_response": translate})


def run_app(env='dev'):
    config_file = f"src/config/config-{env}.ini"
    app_context.use_config(config_file)

    global translate_pipeline
    translate_pipeline = app_context.get('translate_pipeline')
    return app

# Run the FastAPI app
if __name__ == "__main__":
    import uvicorn
    run_app('phuong')
    uvicorn.run(app, host="0.0.0.0", port=8003)