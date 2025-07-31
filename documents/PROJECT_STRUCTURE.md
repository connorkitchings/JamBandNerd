# Project Directory Structure

JamBandNerd/
├── .env
├── .git/
├── .github/
│   └── workflows/
├── .gitignore
├── .devcontainer/
├── .vscode/
├── config/
├── documents/
│   ├── PROJECT_STRUCTURE.md
│   ├──_current_context.md
│   ├── docs_sidebar.json
│   ├── execution/
│   ├── planning/
│   └── dev_logs/
├── logs/
│   ├── Goose/
│   ├── Phish/
│   ├── UM/
│   ├── WSP/
│   ├── wsp/
│   ├── data_collection.log
│   ├── run_all_pipelines.log
│   └── run_all_predict_todays.log
├── README.md
├── requirements.txt
├── scripts/
│   ├── run_all_pipelines.py
│   ├── run_all_predict_todays.py
│   ├── run_goose_pipeline.py
│   ├── run_phish_pipeline.py
│   ├── run_um_pipeline.py
│   └── run_wsp_pipeline.py
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

> __Note:__ This structure follows data science best practices, with modular separation for data
 collection, processing, modeling, prediction, publishing, and documentation.
> __Note on Data Storage:__ The local `data/` directory is deprecated. All data pipelines are being
 migrated to use Supabase as the central data store. The Phish pipeline has been fully migrated,
 and other bands will follow. The `data/` directory may still contain legacy files but is no longer
 the source of truth.
> __Note:__ The `venv` directory, `__pycache__` directories, and `.DS_Store` files are automatically
 generated and can be safely ignored. The `.devcontainer/`, `.vscode/`, `config/`: Environment and
 editor configuration (devcontainer.json, settings.json, etc.)
> __Note:__ Python 3.12.x is recommended for full compatibility (especially for lxml). All
 dependencies are managed through `pyproject.toml` and installed with UV. See the README for
setup steps.
