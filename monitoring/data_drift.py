
from pathlib import Path

import pandas as pd
from evidently import Report
from evidently.presets import DataDriftPreset


def main():
    # Reference data: earlier movie recommendation inputs
    reference = pd.DataFrame({
        "rating": [3, 4, 5, 2, 4, 5, 3, 4, 2, 5],
        "user_activity": [2, 4, 5, 1, 3, 6, 2, 4, 1, 5],
    })

    # Current data: simulated newer inputs
    current = pd.DataFrame({
        "rating": [1, 2, 2, 1, 3, 2, 1, 2, 3, 1],
        "user_activity": [1, 1, 2, 1, 2, 1, 1, 2, 1, 1],
    })

    report = Report([
        DataDriftPreset(),
    ])

    result = report.run(
        reference_data=reference,
        current_data=current,
    )

    output_path = Path("reports/data_drift_report.html")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.save_html(str(output_path))

    print(f"Data drift report saved to: {output_path.resolve()}")


if __name__ == "__main__":
    main()
