import html
import subprocess
from datetime import datetime
from pathlib import Path

from config import OPEN_REPORTS
from run_context import (
    REPORT_DIR,
    unique_artifact_name,
)


def _metadata_html(metadata):
    """Create the test-configuration section of the report."""

    metadata = metadata or {}

    system_name = html.escape(
        str(
            metadata.get(
                "system_name",
                "Not specified",
            )
        )
    )

    units_under_test = ", ".join(
        html.escape(str(item))
        for item in metadata.get(
            "units_under_test",
            [],
        )
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
        str(
            metadata.get(
                "polaris_version",
                "TBD",
            )
        )
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
                <span class="metadata-label">Unit Under Test</span>
                <span class="metadata-value">{system_name}</span>
            </div>

            <div class="metadata-item">
                <span class="metadata-label">Subsystems Under Test</span>
                <span class="metadata-value">{units_under_test}</span>
            </div>

            <div class="metadata-item">
                <span class="metadata-label">Software Test Articles</span>
                <span class="metadata-value">{software_articles}</span>
            </div>

            <div class="metadata-item">
                <span class="metadata-label">Hardware Test Articles</span>
                <span class="metadata-value">{hardware_articles}</span>
            </div>

            <div class="metadata-item">
                <span class="metadata-label">
                    Polaris Software Version
                </span>

                <span class="metadata-value">{polaris_version}</span>

                <span class="metadata-status">
                    Lookup status: {version_status}
                </span>
            </div>
        </div>
    </section>
    """


def _normalize_status(status):
    """Convert result statuses into standard report values."""

    normalized = str(status or "").strip().upper()

    if normalized.startswith("ABORT"):
        return "ABORTED"

    if normalized.startswith("FAIL"):
        return "FAIL"

    if normalized.startswith("WARN"):
        return "WARN"

    return "PASS"


def _normalize_result_item(item):
    """Normalize result keys produced by different step runners."""

    return {
        "test_case": item.get(
            "test_case",
            item.get(
                "test_case_id",
                "UNKNOWN",
            ),
        ),
        "test_name": item.get(
            "test_name",
            item.get(
                "test_case_name",
                "",
            ),
        ),
        "gui": item.get(
            "gui",
            "Unknown",
        ),
        "type": item.get(
            "type",
            item.get(
                "step_type",
                "Unknown",
            ),
        ),
        "step": item.get(
            "step",
            item.get(
                "step_id",
                "—",
            ),
        ),
        "instruction": item.get(
            "instruction",
            "",
        ),
        "expected": item.get(
            "expected",
            "",
        ),
        "actual": item.get(
            "actual",
            "",
        ),
        "status": item.get(
            "status",
            "FAIL",
        ),
        "screenshot": item.get(
            "screenshot",
            item.get("evidence"),
        ),
        "notes": item.get(
            "notes",
            "",
        ),
        "timestamp": item.get(
            "timestamp",
            "",
        ),
    }


def _status_css_class(status):
    """Return the CSS class for a normalized status."""

    normalized = _normalize_status(status)

    if normalized == "PASS":
        return "pass"

    if normalized == "ABORTED":
        return "aborted"

    if normalized == "WARN":
        return "warn"

    return "fail"


def _determine_overall_result(results):
    """Determine the overall result for one test case."""

    statuses = [
        _normalize_status(
            result.get("status")
        )
        for result in results
    ]

    if "ABORTED" in statuses:
        return "ABORTED"

    if "FAIL" in statuses:
        return "FAILED"

    if "WARN" in statuses:
        return "COMPLETED WITH WARNINGS"

    return "PASSED"


def _count_step_types(results):
    """Count automated, manual, and terminal steps."""

    automated_count = 0
    manual_count = 0
    terminal_count = 0

    for item in results:
        step_type = str(
            item.get(
                "type",
                "",
            )
        ).strip().lower()

        if step_type in (
            "auto",
            "automated",
            "squish",
            "gui automation",
        ):
            automated_count += 1

        elif step_type == "manual":
            manual_count += 1

        elif any(
            value in step_type
            for value in (
                "terminal",
                "ssh",
                "command",
            )
        ):
            terminal_count += 1

    return (
        automated_count,
        manual_count,
        terminal_count,
    )


def _screenshot_html(screenshot_path):
    """Create a clickable screenshot preview."""

    if not screenshot_path:
        return "<i>—</i>"

    absolute_path = Path(
        screenshot_path
    ).expanduser().resolve()

    if not absolute_path.exists():
        return "<i>Screenshot unavailable</i>"

    safe_url = html.escape(
        absolute_path.as_uri(),
        quote=True,
    )

    return (
        f'<a href="{safe_url}" target="_blank">'
        f'<img src="{safe_url}" alt="Test screenshot">'
        f"</a>"
    )


def _result_rows_html(
    test_case,
    results,
):
    """Create the table rows for one test case."""

    if not results:
        return """
        <tr>
            <td colspan="11">
                <i>No results were recorded for this test.</i>
            </td>
        </tr>
        """

    rows = ""

    test_id = str(
        test_case.get(
            "id",
            "UNKNOWN",
        )
    )

    for index, item in enumerate(results):
        status = _normalize_status(
            item.get("status")
        )

        status_class = _status_css_class(
            status
        )

        screenshot_html = _screenshot_html(
            item.get("screenshot")
        )

        step_gui = str(
            item.get(
                "gui",
                test_case.get(
                    "gui",
                    "Unknown",
                ),
            )
        )

        step_type = str(
            item.get("type")
            or "Unknown"
        )

        step_value = str(
            item.get("step")
            or "—"
        )

        instruction = str(
            item.get("instruction")
            or "—"
        )

        expected = str(
            item.get("expected")
            or "—"
        )

        actual = str(
            item.get("actual")
            or "—"
        )

        notes = str(
            item.get("notes")
            or "—"
        )

        timestamp_value = str(
            item.get("timestamp")
            or "—"
        )

        if index == 0:
            test_case_cell = (
                f'<td rowspan="{len(results)}">'
                f"{html.escape(test_id)}"
                f"</td>"
            )
        else:
            test_case_cell = ""

        rows += (
            "<tr>"
            f"{test_case_cell}"
            f"<td>{html.escape(step_gui)}</td>"
            f"<td>{html.escape(step_type)}</td>"
            f"<td>{html.escape(step_value)}</td>"
            f'<td class="text-content">'
            f"{html.escape(instruction)}"
            f"</td>"
            f'<td class="text-content">'
            f"{html.escape(expected)}"
            f"</td>"
            f'<td class="terminal-output">'
            f"{html.escape(actual)}"
            f"</td>"
            f'<td class="status-cell {status_class}">'
            f"<b>{html.escape(status)}</b>"
            f"</td>"
            f"<td>{screenshot_html}</td>"
            f'<td class="text-content notes-cell" contenteditable="false">'
            f"{html.escape(notes)}"
            f"</td>"
            f"<td>{html.escape(timestamp_value)}</td>"
            "</tr>"
        )

    return rows


def generate_html_report(
    test_case,
    results,
    metadata=None,
):
    """
    Generate one HTML report for one test case.

    Args:
        test_case:
            Test definition dictionary from tests.py.

        results:
            Results belonging only to this test case.

        metadata:
            Optional system and software metadata.

    Returns:
        Absolute report path as a string.
    """

    REPORT_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    test_id = str(
        test_case.get(
            "id",
            "UNKNOWN",
        )
    )

    test_name = str(
        test_case.get(
            "name",
            "Unnamed Test",
        )
    )

    report_path = (
        REPORT_DIR
        / unique_artifact_name(
            test_id,
            extension="html",
        )
    )

    normalized_results = [
        _normalize_result_item(item)
        for item in results
    ]

    overall_result = _determine_overall_result(
        normalized_results
    )

    total = len(normalized_results)

    passed = sum(
        _normalize_status(
            item["status"]
        ) == "PASS"
        for item in normalized_results
    )

    failed = sum(
        _normalize_status(
            item["status"]
        ) == "FAIL"
        for item in normalized_results
    )

    warnings = sum(
        _normalize_status(
            item["status"]
        ) == "WARN"
        for item in normalized_results
    )

    aborted = sum(
        _normalize_status(
            item["status"]
        ) == "ABORTED"
        for item in normalized_results
    )

    (
        automated_count,
        manual_count,
        terminal_count,
    ) = _count_step_types(
        normalized_results
    )

    rows_html = _result_rows_html(
        test_case,
        normalized_results,
    )

    generated_time = datetime.now().strftime(
        "%Y-%m-%d %H:%M:%S"
    )

    metadata_section = _metadata_html(
        metadata
    )

    overall_class = _status_css_class(
        overall_result
    )

    safe_report_path = html.escape(
        str(report_path)
    )

    report_html = f"""
    <!DOCTYPE html>
    <html lang="en">

    <head>
        <meta charset="UTF-8">

        <meta
            name="viewport"
            content="width=device-width, initial-scale=1.0"
        >

        <title>{html.escape(test_id)} Test Report</title>

        <style>
            body {{
                font-family: Arial, sans-serif;
                margin: 32px;
                color: #222;
                background: #fff;
            }}

            h1 {{
                margin-bottom: 6px;
            }}

            .test-title {{
                margin-top: 0;
                color: #555;
                font-size: 18px;
                font-weight: normal;
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
                text-align: left;
            }}

            th {{
                background: #a6a6a6;
            }}

            img {{
                max-width: 180px;
                height: auto;
                border: 1px solid #bbb;
            }}

            button {{
                padding: 8px 14px;
                margin-right: 8px;
                cursor: pointer;
                border: 1px solid #aaa;
                border-radius: 4px;
                background: #f5f5f5;
            }}

            button:hover {{
                background: #e8e8e8;
            }}

            .summary {{
                border: 1px solid #ccc;
                background: #f7f7f7;
                padding: 16px;
                margin-bottom: 20px;
            }}

            .summary-grid {{
                display: grid;
                grid-template-columns:
                    repeat(auto-fit, minmax(150px, 1fr));
                gap: 10px;
                margin-top: 12px;
            }}

            .summary-item {{
                background: #fff;
                border: 1px solid #ddd;
                padding: 10px;
            }}

            .summary-label {{
                display: block;
                color: #555;
                font-size: 12px;
                font-weight: bold;
                text-transform: uppercase;
            }}

            .summary-value {{
                display: block;
                margin-top: 4px;
                font-size: 17px;
            }}

            .overall-status {{
                display: inline-block;
                padding: 6px 10px;
                border-radius: 4px;
                font-weight: bold;
            }}

            .overall-status.pass {{
                background: #d9f2d9;
                color: #1a7a1a;
            }}

            .overall-status.fail {{
                background: #fbd6d6;
                color: #b30000;
            }}

            .overall-status.aborted {{
                background: #fff1c7;
                color: #9a6700;
            }}

            .overall-status.warn {{
                background: #fff4cc;
                color: #806000;
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

            .status-cell.warn {{
                background: #fff4cc;
                color: #806000;
            }}

            .text-content {{
                white-space: pre-wrap;
                text-align: left;
            }}

            .notes-cell[contenteditable="true"] {{
                background: #fffbe6;
                outline: 2px solid #888;
                cursor: text;
            }}

            .terminal-output {{
                white-space: pre-wrap;
                font-family:
                    "Courier New",
                    Courier,
                    monospace;
                font-size: 11px;
                line-height: 1.35;
                text-align: left;
                padding: 8px;
            }}

            .report-path {{
                margin-top: 15px;
                color: #555;
                font-size: 13px;
                overflow-wrap: anywhere;
            }}

            .test-metadata {{
                border: 1px solid #ccc;
                background: #fff;
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

            @media print {{
                body {{
                    margin: 10px;
                }}

                .summary,
                .test-metadata {{
                    break-inside: avoid;
                }}

                .report-controls {{
                    display: none;
                }}
            }}
        </style>
    </head>

    <body>

        <h1>Test Report: {html.escape(test_id)}</h1>

        <p class="test-title">
            {html.escape(test_name)}
        </p>

        {metadata_section}

        <section class="summary">

            <p>
                <b>Generated:</b>
                {html.escape(generated_time)}
            </p>

            <p>
                <b>Overall Result:</b>

                <span class="overall-status {overall_class}">
                    {html.escape(overall_result)}
                </span>
            </p>

            <div class="summary-grid">

                <div class="summary-item">
                    <span class="summary-label">
                        Total Steps
                    </span>

                    <span class="summary-value">
                        {total}
                    </span>
                </div>

                <div class="summary-item">
                    <span class="summary-label">
                        Passed
                    </span>

                    <span class="summary-value">
                        {passed}
                    </span>
                </div>

                <div class="summary-item">
                    <span class="summary-label">
                        Failed
                    </span>

                    <span class="summary-value">
                        {failed}
                    </span>
                </div>

                <div class="summary-item">
                    <span class="summary-label">
                        Warnings
                    </span>

                    <span class="summary-value">
                        {warnings}
                    </span>
                </div>

                <div class="summary-item">
                    <span class="summary-label">
                        Aborted
                    </span>

                    <span class="summary-value">
                        {aborted}
                    </span>
                </div>

                <div class="summary-item">
                    <span class="summary-label">
                        Automated Steps
                    </span>

                    <span class="summary-value">
                        {automated_count}
                    </span>
                </div>

                <div class="summary-item">
                    <span class="summary-label">
                        Manual Steps
                    </span>

                    <span class="summary-value">
                        {manual_count}
                    </span>
                </div>

                <div class="summary-item">
                    <span class="summary-label">
                        Terminal / SSH Steps
                    </span>

                    <span class="summary-value">
                        {terminal_count}
                    </span>
                </div>

            </div>

            <p class="report-path">
                <b>Report Path:</b>
                {safe_report_path}
            </p>

        </section>

        <div
            class="report-controls"
            style="margin-bottom: 15px;"
        >
            <button
                id="editNotesButton"
                onclick="toggleNotes()"
            >
                Edit Notes
            </button>

            <button
                onclick="saveReport()"
            >
                Save Updated Report
            </button>
        </div>

        <table>

            <thead>
                <tr>
                    <th style="width: 7%;">
                        Test Case
                    </th>

                    <th style="width: 8%;">
                        GUI / Computer
                    </th>

                    <th style="width: 7%;">
                        Type
                    </th>

                    <th style="width: 6%;">
                        Step
                    </th>

                    <th style="width: 10%;">
                        Instruction
                    </th>

                    <th style="width: 10%;">
                        Expected Result
                    </th>

                    <th style="width: 28%;">
                        Actual / Terminal Output
                    </th>

                    <th style="width: 7%;">
                        Status
                    </th>

                    <th style="width: 8%;">
                        Screenshot
                    </th>

                    <th style="width: 7%;">
                        Notes
                    </th>

                    <th style="width: 10%;">
                        Timestamp
                    </th>
                </tr>
            </thead>

            <tbody>
                {rows_html}
            </tbody>

        </table>

        <script>
            let editingNotes = false;

            function toggleNotes() {{
                editingNotes = !editingNotes;

                const editButton =
                    document.getElementById(
                        "editNotesButton"
                    );

                document
                    .querySelectorAll(".notes-cell")
                    .forEach(cell => {{
                        cell.contentEditable =
                            editingNotes
                                ? "true"
                                : "false";
                    }});

                if (editingNotes) {{
                    editButton.textContent =
                        "Done Editing";
                }} else {{
                    editButton.textContent =
                        "Edit Notes";
                }}
            }}

            function saveReport() {{
                editingNotes = false;

                document
                    .querySelectorAll(".notes-cell")
                    .forEach(cell => {{
                        cell.contentEditable =
                            "false";
                    }});

                const editButton =
                    document.getElementById(
                        "editNotesButton"
                    );

                editButton.textContent =
                    "Edit Notes";

                const htmlContent =
                    "<!DOCTYPE html>\\n" +
                    document.documentElement.outerHTML;

                const blob =
                    new Blob(
                        [htmlContent],
                        {{
                            type: "text/html"
                        }}
                    );

                const url =
                    URL.createObjectURL(blob);

                const link =
                    document.createElement("a");

                link.href = url;

                link.download =
                    document.title.replace(
                        /[^a-zA-Z0-9-_]/g,
                        "_"
                    ) + ".html";

                link.click();

                URL.revokeObjectURL(url);
            }}
        </script>

    </body>
    </html>
    """

    with report_path.open(
        "w",
        encoding="utf-8",
    ) as report_file:
        report_file.write(
            report_html
        )

    print(
        f"HTML report generated: {report_path}"
    )

    return str(report_path)


def generate_reports(
    test_results,
    metadata=None,
):
    """
    Generate one report for every test case.

    Expected format:

        [
            (test_case_dictionary, list_of_results),
            (test_case_dictionary, list_of_results),
        ]
    """

    report_paths = []

    for test_case, results in test_results:
        report_path = generate_html_report(
            test_case=test_case,
            results=results,
            metadata=metadata,
        )

        report_paths.append(
            report_path
        )

    return report_paths


def print_summary(results):
    """Print the complete run summary in the terminal."""

    print("\n" + "=" * 60)
    print("TEST EXECUTION SUMMARY")
    print("=" * 60)

    if not results:
        print("No test results were recorded.")
        return

    for raw_item in results:
        item = _normalize_result_item(
            raw_item
        )

        status = _normalize_status(
            item["status"]
        )

        print(
            f"{item['test_case']} "
            f"[{item['step']}] | "
            f"{status}: "
            f"{item['test_name']}"
        )

    total = len(results)

    passed = sum(
        _normalize_status(
            item.get("status")
        ) == "PASS"
        for item in results
    )

    failed = sum(
        _normalize_status(
            item.get("status")
        ) == "FAIL"
        for item in results
    )

    warnings = sum(
        _normalize_status(
            item.get("status")
        ) == "WARN"
        for item in results
    )

    aborted = sum(
        _normalize_status(
            item.get("status")
        ) == "ABORTED"
        for item in results
    )

    print("-" * 60)
    print(f"Total steps: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    print(f"Warnings: {warnings}")
    print(f"Aborted: {aborted}")
    print("=" * 60)


def open_reports(report_paths):
    """
    Open generated reports only when OPEN_REPORTS is enabled.
    """

    if not OPEN_REPORTS:
        return

    for report_path in report_paths:
        try:
            subprocess.Popen(
                [
                    "xdg-open",
                    str(report_path),
                ]
            )

        except OSError as error:
            print(
                "Could not open report "
                f"{report_path}: {error}"
            )