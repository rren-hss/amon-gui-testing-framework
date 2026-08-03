import html
import os
import subprocess
from datetime import datetime
from config import REPORT_PATH
from tests import TEST_STEPS

def _metadata_html(metadata):
    metadata = metadata or {}

    system_name = html.escape(
        str(metadata.get("system_name", "Not specified"))
    )

    units_under_test = ", ".join(
        html.escape(str(item))
        for item in metadata.get("units_under_test", [])
    ) or "Not specified"

    software_articles = ", ".join(
        html.escape(str(item))
        for item in metadata.get(
            "software_test_articles",
            [],
        )
    ) or "Not specified"

    hardware_articles = ", ".join(
        html.escape(str(item))
        for item in metadata.get(
            "hardware_test_articles",
            [],
        )
    ) or "Not specified"

    polaris_version = html.escape(
        str(metadata.get("polaris_version", "TBD"))
    )

    version_status = html.escape(
        str(
            metadata.get(
                "polaris_version_status",
                "UNKNOWN",
            )
        )
    )

    return f"""
    <section class="test-metadata">
        <h2>Test Configuration</h2>

        <div class="metadata-grid">
            <div class="metadata-item">
                <span class="metadata-label">
                    Unit Under Test
                </span>

                <span class="metadata-value">
                    {system_name}
                </span>
            </div>

            <div class="metadata-item">
                <span class="metadata-label">
                    Subsystems Under Test
                </span>

                <span class="metadata-value">
                    {units_under_test}
                </span>
            </div>

            <div class="metadata-item">
                <span class="metadata-label">
                    Software Test Articles
                </span>

                <span class="metadata-value">
                    {software_articles}
                </span>
            </div>

            <div class="metadata-item">
                <span class="metadata-label">
                    Hardware Test Articles
                </span>

                <span class="metadata-value">
                    {hardware_articles}
                </span>
            </div>

            <div class="metadata-item">
                <span class="metadata-label">
                    Polaris Software Version
                </span>

                <span class="metadata-value">
                    {polaris_version}
                </span>

                <span class="metadata-status">
                    Lookup status: {version_status}
                </span>
            </div>
        </div>
    </section>
    """
    
def _normalize_status(status):
    status = str(status or "").upper()

    if status.startswith("ABORT"):
        return "ABORTED"

    if status.startswith("FAIL"):
        return "FAIL"

    return "PASS"


def _normalize_result_item(item):
    return {
        "test_case": item.get(
            "test_case",
            item.get("test_case_id", "UNKNOWN"),
        ),
        "test_name": item.get(
            "test_name",
            item.get("test_case_name", ""),
        ),
        "gui": item.get("gui", "Unknown"),
        "type": item.get(
            "type",
            item.get("step_type", "Unknown"),
        ),
        "step": item.get(
            "step",
            item.get("step_id", "—"),
        ),
        "instruction": item.get("instruction", ""),
        "expected": item.get("expected", ""),
        "actual": item.get("actual", ""),
        "status": item.get("status", "FAIL"),
        "screenshot": item.get(
            "screenshot",
            item.get("evidence"),
        ),
        "notes": item.get("notes", ""),
        "timestamp": item.get("timestamp", ""),
    }


def generate_html_report(results, overall_result, metadata):
    normalized_results = [
        _normalize_result_item(item)
        for item in results
    ]

    grouped_results = {}

    for item in normalized_results:
        test_case_id = str(item["test_case"]).strip()

        if test_case_id not in grouped_results:
            grouped_results[test_case_id] = []

        grouped_results[test_case_id].append(item)

    total = len(normalized_results)

    passed = sum(
        1
        for item in normalized_results
        if _normalize_status(item["status"]) == "PASS"
    )

    failed = sum(
        1
        for item in normalized_results
        if _normalize_status(item["status"]) == "FAIL"
    )

    aborted = sum(
        1
        for item in normalized_results
        if _normalize_status(item["status"]) == "ABORTED"
    )

    rows_html = ""

    for test_definition in TEST_STEPS:
        test_case = test_definition["id"].strip()
        group = grouped_results.get(test_case, [])

        if not group:
            continue

        group_size = len(group)

        group_passed = sum(
            1
            for item in group
            if _normalize_status(item["status"]) == "PASS"
        )

        group_failed = sum(
            1
            for item in group
            if _normalize_status(item["status"]) == "FAIL"
        )

        group_aborted = sum(
            1
            for item in group
            if _normalize_status(item["status"]) == "ABORTED"
        )

        if group_aborted > 0:
            group_status = "ABORTED"
            group_color_class = "aborted"
        elif group_failed > 0:
            group_status = "FAIL"
            group_color_class = "fail"
        else:
            group_status = "PASS"
            group_color_class = "pass"

        automated_count = sum(
            1
            for item in group
            if item["type"].lower() == ("auto", "automated")
        )

        manual_count = sum(
            1
            for item in group
            if item["type"].lower() == "manual"
        )

        test_name = test_definition.get(
            "name",
            group[0].get("test_name", ""),
        )
        gui = test_definition.get(
            "gui",
            group[0].get("gui", "Unknown"),
        )
        
        rows_html += f"""
        <tr class="banner {group_color_class}">
            <td colspan="12">
                <span class="banner-title">
                    {html.escape(str(test_case))} -
                    {html.escape(str(test_name))}
                </span>

                <span class="banner-stats">
                    {group_passed}/{group_size} Steps Passed |
                    {automated_count} Automated /
                    {manual_count} Manual |
                    {group_status}
                </span>
            </td>
        </tr>
            """

        for index, item in enumerate(group):
            status = _normalize_status(item["status"])

            if status == "PASS":
                status_class = "pass"
            elif status == "ABORTED":
                status_class = "aborted"
            else:
                status_class = "fail"

            marker_style = ""

            if group_color_class == "pass":
                border_color = "#1a7a1a"
            elif group_color_class == "aborted":
                border_color = "#9a6700"
            else:
                border_color = "#b30000"

            marker_style = (
                f' style="border-left:4px solid {border_color};'
                f' padding:0;"'
            )        

            screenshot_html = _screenshot_html(
                item.get("screenshot")
            )

            timestamp_value = item.get("timestamp") or "—"
            notes_value = item.get("notes") or "—"
            instruction_value = item.get("instruction") or "—"
            expected_value = item.get("expected") or "—"
            actual_value = item.get("actual") or "—"
            step_value = item.get("step") or "—"
            type_value = item.get("type") or "Unknown"

            if index == 0:
                rows_html += f"""
        <tr>
            <td{marker_style}></td>

            <td rowspan="{group_size}">
                {html.escape(str(test_case))}
            </td>

            <td rowspan="{group_size}">
                {html.escape(str(gui))}
            </td>

            <td>{html.escape(str(type_value))}</td>
            <td>{html.escape(str(step_value))}</td>
            <td>{html.escape(str(instruction_value))}</td>
            <td>{html.escape(str(expected_value))}</td>
            <td>{html.escape(str(actual_value))}</td>

            <td class="status-cell {status_class}">
                <b>{html.escape(status)}</b>
            </td>

            <td>{screenshot_html}</td>
            <td>{html.escape(str(notes_value))}</td>
            <td>{html.escape(str(timestamp_value))}</td>
        </tr>
                """
            else:
                rows_html += f"""
        <tr>
            <td{marker_style}></td>
            <td>{html.escape(str(type_value))}</td>
            <td>{html.escape(str(step_value))}</td>
            <td>{html.escape(str(instruction_value))}</td>
            <td>{html.escape(str(expected_value))}</td>
            <td>{html.escape(str(actual_value))}</td>

            <td class="status-cell {status_class}">
                <b>{html.escape(status)}</b>
            </td>

            <td>{screenshot_html}</td>
            <td>{html.escape(str(notes_value))}</td>
            <td>{html.escape(str(timestamp_value))}</td>
        </tr>
                """

    generated_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )
    metadata_section = _metadata_html(metadata)

    report_html = f"""
<!DOCTYPE html>
<html lang="en">

<head>
    <meta charset="UTF-8">

    <title>Multistep GUI Test Report</title>

    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 40px;
            color: #222;
        }}

        h1 {{
            margin-bottom: 20px;
        }}

        table {{
            border-collapse: collapse;
            width: 100%;
            table-layout: fixed;
        }}

        th,
        td {{
            border: 1px solid #ccc;
            padding: 10px;
            vertical-align: top;
            overflow-wrap: anywhere;
        }}

        th {{
            background: #a6a6a6;
            text-align: left;
        }}

        img {{
            max-width: 160px;
            height: auto;
            border: 1px solid #bbb;
        }}

        .summary {{
            border: 1px solid #ccc;
            background: #f7f7f7;
            padding: 15px;
            margin-bottom: 20px;
        }}

        .status-cell.pass {{
            background: #d9f2d9;
            color: #1a7a1a;
        }}

        .status-cell.fail {{
            background: #fbd6d6;
            color: #b30000;
        }}

        .status-cell.aborted {{
            background: #fff1c7;
            color: #9a6700;
        }}

        tr.banner td {{
            font-weight: bold;
            padding: 8px 10px;
        }}

        tr.banner.pass td {{
            background: #d9f2d9;
            color: #1a7a1a;
        }}

        tr.banner.fail td {{
            background: #fbd6d6;
            color: #b30000;
        }}

        tr.banner.aborted td {{
            background: #fff1c7;
            color: #9a6700;
        }}

        .banner-title {{
            float: left;
        }}

        .banner-stats {{
            float: right;
        }}

        .report-path {{
            font-size: 13px;
            color: #555;
        }}

        .test-metadata {{
            border: 1px solid #ccc;
            background: #ffffff;
            padding: 20px;
            margin-bottom: 20px;
        }}

        .test-metadata h2 {{
            margin-top: 0;
            margin-bottom: 16px;
        }}

        .metadata-grid {{
            display: grid;
            grid-template-columns:
                repeat(auto-fit, minmax(220px, 1fr));
            gap: 12px;
        }}

        .metadata-item {{
            background: #f7f7f7;
            border: 1px solid #ddd;
            padding: 12px;
        }}

        .metadata-label {{
            display: block;
            margin-bottom: 6px;
            color: #555;
            font-size: 12px;
            font-weight: bold;
            text-transform: uppercase;
        }}

        .metadata-value {{
            display: block;
            font-size: 15px;
        }}

        .metadata-status {{
            display: block;
            margin-top: 5px;
            color: #666;
            font-size: 12px;
        }}
    </style>
</head>

<body>

    <h1>Multistep GUI Test Report</h1>
    {metadata_section}
    <div class="summary">
        <p>
            <b>Generated:</b>
            {html.escape(generated_time)}
        </p>

        <p>
            <b>Overall Result:</b>
            {html.escape(str(overall_result))}
        </p>

        <p>
            <b>Total Steps:</b> {total}<br>
            <b>Passed:</b> {passed}<br>
            <b>Failed:</b> {failed}<br>
            <b>Aborted:</b> {aborted}
        </p>

        <p class="report-path">
            <b>Report Path:</b>
            {html.escape(str(REPORT_PATH))}
        </p>
    </div>

    <table>
        <thead>
            <tr>
                <th style="width:8px; padding:0;"></th>
                <th>Test Case</th>
                <th>GUI</th>
                <th>Type</th>
                <th>Step</th>
                <th>Instruction</th>
                <th>Expected Result</th>
                <th>Actual Result</th>
                <th>Status</th>
                <th>Screenshot</th>
                <th>Notes</th>
                <th>Timestamp</th>
            </tr>
        </thead>

        <tbody>
            {rows_html}
        </tbody>
    </table>

</body>
</html>
"""

    report_directory = os.path.dirname(REPORT_PATH)

    if report_directory:
        os.makedirs(report_directory, exist_ok=True)

    with open(
        REPORT_PATH,
        "w",
        encoding="utf-8",
    ) as report_file:
        report_file.write(report_html)

    print(f"HTML report generated: {REPORT_PATH}")

    return REPORT_PATH


def print_summary(results):
    print("\n" + "=" * 60)
    print("MULTISTEP GUI TEST SUMMARY")
    print("=" * 60)

    if not results:
        print("No test results were recorded.")
        return

    for raw_item in results:
        item = _normalize_result_item(raw_item)
        status = _normalize_status(item["status"])

        print(
            f"{item['test_case']} "
            f"[{item['step']}] | "
            f"{status}: "
            f"{item['test_name']}"
        )


def open_report_prompt(report_path=None):
    path = report_path or REPORT_PATH

    response = input(
        "\nWould you like to open the HTML report? "
        "TYPE YES or NO: "
    ).strip().upper()

    if response == "YES":
        subprocess.Popen(
            ["xdg-open", path]
        )


def _screenshot_html(screenshot_path):
    if not screenshot_path:
        return "<i>—</i>"

    absolute_path = os.path.abspath(
        str(screenshot_path)
    )

    if not os.path.exists(absolute_path):
        return "<i>Screenshot unavailable</i>"

    file_url = "file://" + absolute_path
    safe_url = html.escape(
        file_url,
        quote=True,
    )

    return (
        f'<a href="{safe_url}" target="_blank">'
        f'<img src="{safe_url}" '
        f'alt="Test screenshot">'
        f"</a>"
    )