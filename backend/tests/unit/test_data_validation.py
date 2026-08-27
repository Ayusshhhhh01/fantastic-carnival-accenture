import pandas as pd
import pytest

from backend.app.infrastructure.data.validators import validate_frames


def test_data_validation_rejects_missing_columns():
    empty = pd.DataFrame()
    with pytest.raises(ValueError, match="sales is missing"):
        validate_frames((empty, empty, empty, empty))
