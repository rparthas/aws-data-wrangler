"""Amazon CSV S3 Write Module (PRIVATE)."""

import logging
from typing import Dict, List, Optional, Tuple

import boto3  # type: ignore
import pandas as pd  # type: ignore

from awswrangler import _data_types, _utils, catalog, exceptions

_logger: logging.Logger = logging.getLogger(__name__)

_COMPRESSION_2_EXT: Dict[Optional[str], str] = {None: "", "gzip": ".gz", "snappy": ".snappy"}


def _apply_dtype(
    df: pd.DataFrame,
    mode: str,
    database: Optional[str],
    table: Optional[str],
    dtype: Dict[str, str],
    boto3_session: boto3.Session,
) -> pd.DataFrame:
    if (mode in ("append", "overwrite_partitions")) and (database is not None) and (table is not None):
        catalog_types: Optional[Dict[str, str]] = catalog.get_table_types(
            database=database, table=table, boto3_session=boto3_session
        )
        if catalog_types is not None:
            for k, v in catalog_types.items():
                dtype[k] = v
    df = _data_types.cast_pandas_with_athena_types(df=df, dtype=dtype)
    return df


def _validate_args(
    df: pd.DataFrame,
    table: Optional[str],
    dataset: bool,
    path: str,
    partition_cols: Optional[List[str]],
    mode: Optional[str],
    description: Optional[str],
    parameters: Optional[Dict[str, str]],
    columns_comments: Optional[Dict[str, str]],
) -> None:
    if df.empty is True:
        raise exceptions.EmptyDataFrame()
    if dataset is False:
        if path.endswith("/"):
            raise exceptions.InvalidArgumentValue(
                "If <dataset=False>, the argument <path> should be a object path, not a directory."
            )
        if partition_cols:
            raise exceptions.InvalidArgumentCombination("Please, pass dataset=True to be able to use partition_cols.")
        if mode is not None:
            raise exceptions.InvalidArgumentCombination("Please pass dataset=True to be able to use mode.")
        if any(arg is not None for arg in (table, description, parameters, columns_comments)):
            raise exceptions.InvalidArgumentCombination(
                "Please pass dataset=True to be able to use any one of these "
                "arguments: database, table, description, parameters, "
                "columns_comments."
            )


def _sanitize(
    df: pd.DataFrame, dtype: Dict[str, str], partition_cols: List[str]
) -> Tuple[pd.DataFrame, Dict[str, str], List[str]]:
    df = catalog.sanitize_dataframe_columns_names(df=df)
    partition_cols = [catalog.sanitize_column_name(p) for p in partition_cols]
    dtype = {catalog.sanitize_column_name(k): v.lower() for k, v in dtype.items()}
    _utils.check_duplicated_columns(df=df)
    return df, dtype, partition_cols
