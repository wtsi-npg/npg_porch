# FastAPI Server for Pipeline Orchestration Project

## Requirements

Python >= 3.7

## Installation & Usage

To run the server, please execute the following from the root directory:

```bash
bash
pip3 install -r requirements.txt
cd server
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

and open your browser at `http://localhost:8080` to see links to the docs.
