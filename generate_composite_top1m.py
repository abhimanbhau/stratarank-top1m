#!/usr/bin/env python3
"""
Composite Top 1M Domain List Generator
=====================================
This script downloads domain lists from multiple high-quality sources worldwide
and combines them using the Dowdall scoring method (Tranco methodology) to create
a comprehensive, manipulation-resistant top 1 million domain list.

Author: Generated for comprehensive domain analysis
Date: November 2025
License: MIT
"""

import requests
import zipfile
import io
import pandas as pd
import numpy as np
from collections import defaultdict
from datetime import datetime
import time

# Configuration
SOURCES = {
    'Tranco': {
        'url': 'https://tranco-list.eu/top-1m.csv.zip',
        'format': 'csv_zip',
        'columns': ['rank', 'domain'],
        'weight': 1.5,
        'description': 'Research-oriented composite list (30-day avg)'
    },
    'Cisco_Umbrella': {
        'url': 'https://s3-us-west-1.amazonaws.com/umbrella-static/top-1m.csv.zip',
        'format': 'csv_zip',
        'columns': ['rank', 'domain'],
        'weight': 1.3,
        'description': 'DNS query data from 100B+ requests/day'
    },
    'Majestic': {
        'url': 'https://downloads.majestic.com/majestic_million.csv',
        'format': 'csv',
        'columns': ['GlobalRank', 'Domain'],
        'rename': {'GlobalRank': 'rank', 'Domain': 'domain'},
        'weight': 1.2,
        'description': 'Backlink-based ranking (referring subnets)'
    },
    'BuiltWith': {
        'url': 'https://builtwith.com/dl/builtwith-top1m.zip',
        'format': 'csv_zip',
        'columns': ['rank', 'domain'],
        'weight': 1.0,
        'description': 'Technology spend and investment ranking'
    },
    'DomCop': {
        'url': 'https://www.domcop.com/files/top/top10milliondomains.csv.zip',
        'format': 'csv_zip',
        'columns': ['rank', 'domain', 'pagerank'],
        'limit': 1000000,
        'weight': 1.1,
        'description': 'Open PageRank from CommonCrawl'
    },
    'CrUX': {
        'url': 'https://raw.githubusercontent.com/zakird/crux-top-lists/main/data/global/current.csv.gz',
        'format': 'csv_gz',
        'columns': ['origin', 'rank'],
        'process': 'extract_domain_from_origin',
        'weight': 1.4,
        'description': 'Chrome User Experience Report data'
    }
}

def download_and_parse(source_name, config):
    """Download and parse a domain list from a source."""
    print(f"\nDownloading {source_name}...")
    print(f"  Description: {config['description']}")

    try:
        response = requests.get(config['url'], timeout=120)
        response.raise_for_status()

        # Parse based on format
        if config['format'] == 'csv_zip':
            with zipfile.ZipFile(io.BytesIO(response.content)) as z:
                filename = z.namelist()[0]
                with z.open(filename) as f:
                    if source_name == 'Majestic':
                        df = pd.read_csv(f)
                    else:
                        # Read without header, then assign column names
                        df = pd.read_csv(f, header=None, dtype=str)
                        if len(df.columns) >= len(config['columns']):
                            df.columns = config['columns'][:len(df.columns)]
                        else:
                            print(f"  ✗ Not enough columns in {source_name}")
                            return None

        elif config['format'] == 'csv_gz':
            df = pd.read_csv(io.BytesIO(response.content), compression='gzip')

        elif config['format'] == 'csv':
            df = pd.read_csv(io.StringIO(response.text))

        # Process and normalize
        if 'rename' in config:
            df = df.rename(columns=config['rename'])

        if 'process' in config and config['process'] == 'extract_domain_from_origin':
            # Extract domain from origin (e.g., https://www.example.com -> www.example.com)
            df['domain'] = df['origin'].str.replace(r'^https?://', '', regex=True).str.strip()
            df = df[['domain', 'rank']].copy()

        # Ensure we have rank and domain columns
        if 'rank' not in df.columns or 'domain' not in df.columns:
            print(f"  ✗ Missing required columns in {source_name}")
            return None

        df = df[['rank', 'domain']].copy()

        # *** FIX: Convert rank to integer ***
        try:
            df['rank'] = pd.to_numeric(df['rank'], errors='coerce').astype('Int64')
        except Exception as e:
            print(f"  ✗ Error converting rank to integer: {e}")
            return None

        # Apply limit if specified
        if 'limit' in config:
            df = df.head(config['limit'])

        # Clean data
        df['domain'] = df['domain'].str.strip().str.lower()
        df = df.dropna()
        df = df[df['domain'] != '']
        df = df[df['rank'] > 0]  # Remove invalid ranks

        # Sort by rank
        df = df.sort_values('rank').reset_index(drop=True)

        print(f"  ✓ Downloaded {len(df):,} domains from {source_name}")
        return df, config['weight']

    except Exception as e:
        print(f"  ✗ Error downloading {source_name}: {e}")
        import traceback
        traceback.print_exc()
        return None

def dowdall_score(rank, list_size):
    """
    Calculate Dowdall score for a rank.
    Dowdall scoring: 1/rank
    This gives higher scores to top-ranked domains.
    """
    if pd.isna(rank) or rank <= 0:
        return 0
    return 1.0 / float(rank)

def combine_lists_with_dowdall(datasets, target_size=1000000):
    """
    Combine multiple domain lists using Dowdall scoring method.
    """
    print("\n" + "="*80)
    print("COMBINING LISTS USING DOWDALL SCORING METHOD")
    print("="*80)

    # Calculate scores for each domain in each list
    domain_scores = defaultdict(lambda: {'scores': [], 'weights': [], 'appearances': 0})

    for source_name, (df, weight) in datasets.items():
        list_size = len(df)
        print(f"\nProcessing {source_name} ({list_size:,} domains, weight={weight})...")

        for idx, row in df.iterrows():
            domain = row['domain']
            rank = row['rank']

            # *** FIX: Ensure rank is numeric ***
            if pd.isna(rank) or rank <= 0:
                continue

            score = dowdall_score(rank, list_size)
            if score > 0:
                domain_scores[domain]['scores'].append(score)
                domain_scores[domain]['weights'].append(weight)
                domain_scores[domain]['appearances'] += 1

    # Calculate weighted average score for each domain
    print("\nCalculating composite scores...")
    composite_data = []

    for domain, data in domain_scores.items():
        if data['appearances'] == 0:
            continue

        # Weighted average of Dowdall scores
        weighted_score = sum(s * w for s, w in zip(data['scores'], data['weights']))
        total_weight = sum(data['weights'])
        avg_score = weighted_score / total_weight if total_weight > 0 else 0

        # Bonus for appearing in multiple lists (stability bonus)
        stability_bonus = 1 + (data['appearances'] - 1) * 0.1
        final_score = avg_score * stability_bonus

        composite_data.append({
            'domain': domain,
            'composite_score': final_score,
            'appearances': data['appearances'],
            'avg_score': avg_score
        })

    # Create DataFrame and sort by composite score
    composite_df = pd.DataFrame(composite_data)
    composite_df = composite_df.sort_values('composite_score', ascending=False).reset_index(drop=True)
    composite_df['rank'] = range(1, len(composite_df) + 1)

    # Limit to target size
    composite_df = composite_df.head(target_size)

    print(f"\n✓ Generated composite list with {len(composite_df):,} domains")

    # Statistics
    if len(composite_df) > 0:
        appearances_by_list = {}
        for i in range(1, len(datasets) + 1):
            count = len(composite_df[composite_df['appearances'] == i])
            if count > 0:
                appearances_by_list[i] = count

        for appearances, count in sorted(appearances_by_list.items(), reverse=True):
            print(f"  - Domains appearing in {appearances} list{'s' if appearances != 1 else ''}: {count:,}")

    return composite_df

def main():
    """Main execution function."""
    print("="*80)
    print("COMPOSITE TOP 1M DOMAIN LIST GENERATOR")
    print("="*80)
    print(f"Start time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Download all lists
    datasets = {}

    for source_name, config in SOURCES.items():
        result = download_and_parse(source_name, config)
        if result is not None:
            datasets[source_name] = result
        time.sleep(1)  # Be respectful to servers

    if len(datasets) == 0:
        print("\n✗ ERROR: No datasets were successfully downloaded!")
        return

    print(f"\n✓ Successfully downloaded {len(datasets)}/{len(SOURCES)} sources")

    # Combine using Dowdall method
    composite_df = combine_lists_with_dowdall(datasets, target_size=1000000)

    # Save results
    print("\n" + "="*80)
    print("SAVING RESULTS")
    print("="*80)

    # Full composite list with metadata
    output_file_full = f'composite_top1m_full_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    composite_df.to_csv(output_file_full, index=False)
    print(f"\n✓ Saved full composite list: {output_file_full}")
    print(f"  Columns: rank, domain, composite_score, appearances, avg_score")
    print(f"  Rows: {len(composite_df):,}")

    # Simple rank,domain format (compatible with Alexa/Umbrella format)
    output_file_simple = f'composite_top1m_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv'
    composite_df[['rank', 'domain']].to_csv(output_file_simple, index=False, header=False)
    print(f"\n✓ Saved simple format: {output_file_simple}")
    print(f"  Format: rank,domain (no header, compatible with standard lists)")

    # Statistics
    print("\n" + "="*80)
    print("STATISTICS")
    print("="*80)
    print(f"\nTop 20 domains in composite list:")
    print(composite_df[['rank', 'domain', 'appearances']].head(20).to_string(index=False))

    print(f"\n\nDistribution by number of source appearances:")
    appearances_dist = composite_df['appearances'].value_counts().sort_index(ascending=False)
    print(appearances_dist)

    print(f"\n\nComposite score statistics:")
    print(f"  - Max score: {composite_df['composite_score'].max():.6f}")
    print(f"  - Min score: {composite_df['composite_score'].min():.6f}")
    print(f"  - Mean score: {composite_df['composite_score'].mean():.6f}")
    print(f"  - Median score: {composite_df['composite_score'].median():.6f}")

    print(f"\nEnd time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*80)
    print("COMPLETE!")
    print("="*80)

if __name__ == '__main__':
    main()
