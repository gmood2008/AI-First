"""
Pandas / math capability handlers (math.pandas.* namespace).

Implements math.pandas.calculate for financial report workflow.
"""

from typing import Any, Dict, List

from ..handler import ActionHandler
from ..types import ActionOutput


class PandasCalculateHandler(ActionHandler):
    """Handler for math.pandas.calculate."""

    def execute(self, params: Dict[str, Any], context: Any) -> ActionOutput:
        data = params["data"]
        operations = params.get("operations") or []

        try:
            import pandas as pd
        except ImportError:
            return ActionOutput(
                result={
                    "calculated_metrics": {},
                    "success": False,
                    "error_message": "pandas is required for math.pandas.calculate. Install with: pip install pandas",
                },
                undo_closure=None,
                description="math.pandas.calculate: missing pandas",
            )

        if not data:
            return ActionOutput(
                result={"calculated_metrics": {}, "success": True},
                undo_closure=None,
                description="math.pandas.calculate: no data",
            )

        try:
            # Normalize input: accept output of io.pdf.extract_table (list of {page, rows, headers})
            if isinstance(data, list) and data and isinstance(data[0], dict) and "rows" in data[0]:
                rows = []
                for t in data:
                    rows.extend(t.get("rows") or [])
                data = rows if rows else data
            if isinstance(data, list) and data and isinstance(data[0], dict):
                df = pd.DataFrame(data)
            elif isinstance(data, list) and data and isinstance(data[0], (list, tuple)):
                df = pd.DataFrame(data[1:], columns=data[0] if data else None)
            else:
                df = pd.DataFrame(data) if data else pd.DataFrame()

            metrics = {}
            for op in operations:
                if not isinstance(op, dict):
                    continue
                op_type = (op.get("type") or "").strip().lower()
                output_col = op.get("output_column") or "result"

                if op_type == "sum":
                    col = op.get("column")
                    if col and col in df.columns:
                        metrics[output_col] = float(df[col].sum())
                elif op_type == "mean":
                    col = op.get("column")
                    if col and col in df.columns:
                        metrics[output_col] = float(df[col].mean())
                elif op_type == "calculate" and op.get("formula"):
                    formula = str(op["formula"]).strip()
                    try:
                        result = df.eval(formula)
                        if hasattr(result, "iloc"):
                            metrics[output_col] = float(result.mean() if len(result) > 1 else result.iloc[0])
                        else:
                            metrics[output_col] = float(result)
                    except Exception:
                        metrics[output_col] = None

            return ActionOutput(
                result={"calculated_metrics": metrics, "success": True},
                undo_closure=None,
                description=f"math.pandas.calculate: computed {len(metrics)} metric(s)",
            )
        except Exception as e:
            return ActionOutput(
                result={"calculated_metrics": {}, "success": False, "error_message": str(e)},
                undo_closure=None,
                description="math.pandas.calculate: failed",
            )
