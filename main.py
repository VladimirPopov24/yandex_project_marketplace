import os
import sys

project_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "yandex_project_marketplace")
os.chdir(project_dir)
sys.path.insert(0, project_dir)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=False)
