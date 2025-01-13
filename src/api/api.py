from flasgger import Swagger
from flask import Flask, request
from werkzeug.utils import secure_filename

from src.utils.utils import *
from src.app_config import app_context
from flask_cors import CORS

"""
Start data_app:
$ export PYTHONPATH=.
$ gunicorn --bind 0.0.0.0:8081 'data_manager.controllers.data_app:run_app(env="unittest")'
"""

app = Flask(__name__)
app.config['SWAGGER'] = {
    'doc_dir': 'src/api/docs',
    "title": "vOffice Translate",
    "uiversion": 3,
}
CORS(app, resources={r"/*" : {"origins" : "*",
                             "methods": ["*"],
                              "allow_headers": ["*"]
                             }},
    supports_credentials=True)

home_dir = os.getcwd()
UPLOAD_FOLDER = os.path.join(home_dir, "data/upload")
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

swagger = Swagger(app)


@app.route("/translate-docs/status")
def status():
    return ok(
        {
            'status': 'OK'
        }
    )

@app.route("/translate-docs/process-file-vi2en", methods=["POST"])
async def process_file_vi2en():
    ## SAVE FILE PDF
    # read file from request form
    pdf_file = request.files['file']
    file_name = secure_filename(pdf_file.filename).lower()

    # save file
    # create a save path with save folder and filename
    save_path = save_file(pdf_file, UPLOAD_FOLDER)
    # check pdf file is "Really a PDF"
    # this check file extension and the content
    is_valid = pdf_validation(save_path)
    if not is_valid: return error("File error", 415)

    ## PROCESS PDF FILE
    try:
        translate = translate_pipeline.process(path=save_path, en_vi = False)
    except:
        translate = translate_pipeline.raw_process_file(path=save_path, en_vi = False)
    ## INSERT DATA TO DB
    # if cannot establish conection to db, keep pdf file
    # inserted = translate_service.insert_item(
    #     {"doc_id": request.form['doc_id'],
    #     "title": file_name,
    #     "translate": translate,
    #     "uploaded_time": get_file_modification(save_path)}
    # )

    # folder = "delete" if inserted else "reload"
    # action_after_process_file(save_path, folder=folder)

    # return ok({"translate": translate}, 201)
    return {"bot_response" : translate}

@app.route("/translate-docs/process-file-en2vi", methods=["POST"])
async def process_file_en2vi():
    ## SAVE FILE PDF
    # read file from request form
    pdf_file = request.files['file']
    file_name = secure_filename(pdf_file.filename).lower()

    # save file
    # create a save path with save folder and filename
    save_path = save_file(pdf_file, UPLOAD_FOLDER)
    # check pdf file is "Really a PDF"
    # this check file extension and the content
    is_valid = pdf_validation(save_path)
    if not is_valid: return error("File error", 415)

    ## PROCESS PDF FILE
    try:
        translate = translate_pipeline.process(path=save_path, en_vi = True)
    except:
        translate = translate_pipeline.raw_process_file(path=save_path,en_vi = True)

    ## INSERT DATA TO DB
    # if cannot establish conection to db, keep pdf file
    # inserted = translate_service.insert_item(
    #     {"doc_id": request.form['doc_id'],
    #     "title": file_name,
    #     "translate": translate,
    #     "uploaded_time": get_file_modification(save_path)}
    # )

    # folder = "delete" if inserted else "reload"
    # action_after_process_file(save_path, folder=folder)

    # return ok({"translate": translate}, 201)
    return {"bot_response" : translate}


# @app.route("/translate-docs/process-doc", methods=["POST"])
# async def process_doc():
#     try:
#         doc = request.get_json()["doc"]
#     except:
#         return error("Content error", 400)

#     # get related doc from data
#     translate = translate_pipeline.process(doc=doc)

#     return ok({"translate": translate}, 200)

@app.route("/translate-docs/process-raw-docs-vi2en", methods=["POST"])
async def process_raw_docs_vi2en():
    try:
        docs = request.get_json()["docs"]
    except:
        # return error("Content error", 400)
        return {"bot_response" : "Không dịch được với thông tin đã cung cấp!!"}

    # get related doc from data
    translate = translate_pipeline.raw_process(docs=docs, en_vi = False)

    # return ok({"translate": translate}, 200)
    return {"bot_response" : translate}

@app.route("/translate-docs/process-raw-docs-en2vi", methods=["POST"])
async def process_raw_docs_en2vi():
    try:
        docs = request.get_json()["docs"]
    except:
        # return error("Content error", 400)
        return {"bot_response" : "Không dịch được với thông tin đã cung cấp!!"}

    # get related doc from data
    translate = translate_pipeline.raw_process(docs=docs, en_vi = True)

    return {"bot_response" : translate}    
    # return ok({"translate": translate}, 200) 


# @app.route("/translate-docs/get-translate", methods=["GET"])
# async def get_translate():
#     doc_id = request.args.get("doc_id")

#     # get related docs from db
#     translate = translate_service.get_item(doc_id)

#     if translate is not None and len(translate) > 0:
#         return ok(translate, 200)
#   else:
#         return ok("", 204)


def run_app(env='dev'):
    config_file = "src/config/config-%s.ini" % env
    app_context.use_config(config_file)

    global translate_pipeline
    translate_pipeline = app_context.get('translate_pipeline')

    # global translate_service
    # translate_service = app_context.get('translate_service')

    return app

if __name__ == "__main__":
    run_app('phuong')
    app.run(host="0.0.0.0", port=8003)