---
layout: default
title: Getting Started
---

# Getting Started

This guide will walk you through the steps to generate the composite top 1M domain list on your local machine.

## 1. Prerequisites

- Python 3.8 or higher
- `pip` for installing packages

## 2. Installation

First, clone the repository to your local machine:

```bash
git clone https://github.com/abhimanbhau/stratarank-top1m.git
cd stratarank-top1m
```

Next, install the required Python dependencies using the `requirements.txt` file:

```bash
pip install -r requirements.txt
```

This will install `pandas`, `numpy`, and `requests`.

## 3. Running the Script

Execute the generation script from the root of the project directory:

```bash
python generate_composite_top1m.py
```

The script will begin downloading the latest domain lists from all sources and processing them. This process typically takes between **5 to 15 minutes**, depending on your network speed.

## 4. Output Files

Once the script completes, it will create two new CSV files in the project's root directory, timestamped with the current date (YYYYMMDD):

-   `composite_top1m_YYYYMMDD.csv`: A simple list containing two columns: `rank` and `domain`.
-   `composite_top1m_full_YYYYMMDD.csv`: An enhanced list with additional metadata, including the composite score and the number of source lists the domain appeared in.

<br>

[<-- Back to Home](index.html)
