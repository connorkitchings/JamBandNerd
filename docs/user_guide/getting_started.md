# Getting Started

Welcome to the JamBandNerd project! This guide will help you get set up and running.

## 1. Project Overview

JamBandNerd is a data science platform for collecting, transforming, and predicting jam band setlists. The project is built with Python and uses Supabase for the database, and Streamlit for the web interface.

The project is designed to be modular and extensible, so you can easily add new bands, models, or features.

## 2. Installation & Setup

### Prerequisites

- Python 3.12+
- [UV package manager](https://github.com/astral-sh/uv) (recommended)
- Git
- A Supabase account (for database access)

### Installation

Please follow these steps to set up your local environment.

1. **Clone and setup environment:**

    ```bash
    git clone https://github.com/connorkitchings/JamBandNerd.git
    cd JamBandNerd
    uv venv --python=3.12
    source .venv/bin/activate
    uv pip install .
    ```

2. **Environment Variables**:

    Before you can run the project, you will need to set up your environment variables. Copy the `.env.example` file to a new file named `.env` and fill in the required values for your Supabase project.

    ```bash
    SUPABASE_URL=your_supabase_url
    SUPABASE_KEY=your_supabase_key
    PHISH_API_KEY=your_phish_net_key  # Optional, for Phish data only
    ```
