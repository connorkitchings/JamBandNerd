# Project Directory Structure

JamBandNerd/
├── .env
├── .git/
├── .github/
│   └── workflows/
├── .gitignore
├── logs/
│   ├── Goose/
│   ├── Phish/
│   ├── WSP/
│   └── data_collection.log
├── main.py
├── PROJECT_STRUCTURE.md
├── README.md
├── requirements.txt
├── data/
│   ├── README.md
│   ├── goose/
│   ├── phish/
│   ├── um/
│   └── wsp/
├── scripts/
│   ├── make_all_predictions.py
│   └── run_all_pipelines.py
├── src/
│   └── jambandnerd/
│       ├── __init__.py
│       ├── common/
│       │   └── utils/
│       │       ├── common_utils.py
│       │       ├── logger.py
│       │       └── __init__.py
│       ├── data_collection/
│       │   ├── goose/
│       │   ├── phish/
│       │   ├── um/
│       │   └── wsp/
│       ├── data_processing/
│       │   └── __init__.py
│       └── predictions/
│           ├── ckplus_model/
│           ├── notebook_model/
│           └── __init__.py
├── tests/
│   └── __init__.py
├── venv/
├── web/
│   ├── Images/
│   └── streamlit-app/

> __Note:__ This structure follows data science best practices, with modular separation for data collection, processing, modeling, prediction, and publishing. Adjust subfolders as needed for your specific project components.
> __Note:__ The `venv` directory, `__pycache__` directories, and `.DS_Store` files are automatically generated and can be safely ignored.
