"""
Convert JSONL data to Parquet format.

Parquet offers:
- Efficient columnar storage
- Better compression
- Fast analytical queries
- Compatible with Pandas, Spark, DuckDB
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)


def load_jsonl(filepath: str) -> List[Dict[str, Any]]:
    """Load articles from JSONL file."""
    articles = []
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                articles.append(json.loads(line))
    return articles


def convert_to_parquet(
    input_path: str,
    output_path: str = None,
    compression: str = 'snappy'
) -> str:
    """
    Convert JSONL file to Parquet format.
    
    Args:
        input_path: Path to input JSONL file
        output_path: Path for output Parquet file (auto-generated if None)
        compression: Compression codec ('snappy', 'gzip', 'zstd')
        
    Returns:
        Path to output Parquet file
    """
    try:
        import pandas as pd
    except ImportError:
        raise ImportError("pandas is required for Parquet conversion. Install with: pip install pandas pyarrow")
    
    try:
        import pyarrow  # noqa
    except ImportError:
        raise ImportError("pyarrow is required for Parquet conversion. Install with: pip install pyarrow")
    
    # Generate output path if not provided
    if output_path is None:
        input_file = Path(input_path)
        output_path = str(input_file.with_suffix('.parquet'))
    
    logger.info(f"Loading {input_path}...")
    articles = load_jsonl(input_path)
    logger.info(f"Loaded {len(articles)} articles")
    
    # Convert to DataFrame
    df = pd.DataFrame(articles)
    
    # Ensure consistent column types
    if 'tokens' in df.columns:
        df['tokens'] = df['tokens'].fillna(0).astype(int)
    
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'], errors='coerce')
    
    if 'crawled_at' in df.columns:
        df['crawled_at'] = pd.to_datetime(df['crawled_at'], errors='coerce')
    
    # Handle list columns (convert to string for Parquet compatibility)
    for col in ['named_entities', 'tags']:
        if col in df.columns:
            df[col] = df[col].apply(lambda x: json.dumps(x) if isinstance(x, list) else x)
    
    # Save to Parquet
    logger.info(f"Saving to {output_path}...")
    df.to_parquet(output_path, compression=compression, index=False)
    
    # Log file size comparison
    input_size = Path(input_path).stat().st_size / (1024 * 1024)
    output_size = Path(output_path).stat().st_size / (1024 * 1024)
    compression_ratio = (1 - output_size / input_size) * 100 if input_size > 0 else 0
    
    logger.info(f"Conversion complete!")
    logger.info(f"  Input size:  {input_size:.2f} MB")
    logger.info(f"  Output size: {output_size:.2f} MB")
    logger.info(f"  Compression: {compression_ratio:.1f}% reduction")
    
    return output_path


def convert_all(
    input_dir: str = "data/processed",
    output_dir: str = None,
    compression: str = 'snappy'
) -> List[str]:
    """
    Convert all JSONL files in a directory to Parquet.
    
    Args:
        input_dir: Directory containing JSONL files
        output_dir: Output directory (same as input if None)
        compression: Compression codec
        
    Returns:
        List of output Parquet file paths
    """
    input_path = Path(input_dir)
    output_path = Path(output_dir) if output_dir else input_path
    output_path.mkdir(parents=True, exist_ok=True)
    
    jsonl_files = list(input_path.glob("*.jsonl"))
    
    if not jsonl_files:
        logger.warning(f"No JSONL files found in {input_dir}")
        return []
    
    logger.info(f"Found {len(jsonl_files)} JSONL files to convert")
    
    output_files = []
    for jsonl_file in jsonl_files:
        parquet_file = output_path / jsonl_file.with_suffix('.parquet').name
        try:
            convert_to_parquet(str(jsonl_file), str(parquet_file), compression)
            output_files.append(str(parquet_file))
        except Exception as e:
            logger.error(f"Failed to convert {jsonl_file}: {e}")
    
    return output_files


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
    )
    
    parser = argparse.ArgumentParser(description="Convert JSONL to Parquet")
    parser.add_argument("input", nargs="?", default="data/processed",
                       help="Input JSONL file or directory")
    parser.add_argument("--output", "-o", help="Output path")
    parser.add_argument("--compression", "-c", default="snappy",
                       choices=['snappy', 'gzip', 'zstd'],
                       help="Compression codec")
    parser.add_argument("--all", "-a", action="store_true",
                       help="Convert all JSONL files in directory")
    
    args = parser.parse_args()
    
    if args.all or Path(args.input).is_dir():
        output_files = convert_all(args.input, args.output, args.compression)
        print(f"\nConverted {len(output_files)} files to Parquet")
    else:
        output_file = convert_to_parquet(args.input, args.output, args.compression)
        print(f"\nSaved to {output_file}")
