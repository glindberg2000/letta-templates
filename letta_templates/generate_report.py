#!/usr/bin/env python3

import argparse
import os
import re
from datetime import datetime
from typing import Dict, List, Optional

class TestSection:
    def __init__(self, name: str, description: str):
        self.name = name
        self.description = description
        self.dialogs: List[Dict] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

class TestReport:
    def __init__(self):
        self.config: Dict = {}
        self.sections: List[TestSection] = []
        self.start_time: Optional[datetime] = None
        self.end_time: Optional[datetime] = None

def parse_dialog_section(f, timestamp) -> Dict:
    """Parse a complete dialog section including context and evaluations"""
    dialog = {"timestamp": timestamp}
    
    while True:
        line = next(f, '').strip()
        if not line or "-------------------" in line:
            break
            
        if line == "Dialog:":
            continue
            
        # Track speakers and context
        if " says:" in line:
            speaker = line.split(" says:")[0]
            message = next(f, '').strip()
            dialog.setdefault("conversation", []).append({
                "speaker": speaker,
                "message": message
            })
            
        # Track agent responses
        elif line.startswith("Q: "):
            dialog["agent_response"] = line[3:]
        elif line.startswith("[Internal Reasoning: "):
            dialog["reasoning"] = line[19:-1]
        elif line.startswith("A: "):
            dialog["action_result"] = line[3:]
            
        # Track evaluations
        elif "Response Evaluation:" in line:
            eval_results = {}
            while True:
                line = next(f, '').strip()
                if not line or "-------------------" in line:
                    break
                if line.startswith("✓"):
                    key, value = line[2:].split(":", 1)
                    eval_results[key.strip()] = value.strip()
                elif line.startswith("Explanation:"):
                    eval_results["explanation"] = line[12:].strip()
            dialog["evaluation"] = eval_results
            
        # Track test results
        elif line.startswith("✓") or line.startswith("✗"):
            dialog.setdefault("test_results", []).append(line.strip())
            
    return dialog

def parse_log_file(log_file: str) -> TestReport:
    report = TestReport()
    current_section = None
    current_dialog = {}
    
    timestamp_pattern = r"(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})"
    
    with open(log_file, 'r') as f:
        for line in f:
            # Parse timestamp
            timestamp_match = re.match(timestamp_pattern, line)
            if timestamp_match:
                timestamp = datetime.strptime(timestamp_match.group(1), "%Y-%m-%d %H:%M:%S,%f")
                
                # Update report timing
                if not report.start_time:
                    report.start_time = timestamp
                report.end_time = timestamp
            
            # Parse configuration
            if "Configuration:" in line:
                while True:
                    line = next(f, '').strip()
                    if not line or "===" in line:
                        break
                    if ":" in line:
                        key, value = line.split(":", 1)
                        report.config[key.strip()] = value.strip()
            
            # Parse test sections
            elif "=== " in line and " ===" in line:
                section_name = line.strip().replace("===", "").strip()
                description = next(f, '').strip()
                current_section = TestSection(section_name, description)
                report.sections.append(current_section)
                current_section.start_time = timestamp
            
            # Enhanced dialog parsing
            if "=== DIALOG DETAILS ===" in line:
                dialog = parse_dialog_section(f, timestamp)
                if current_section and dialog:
                    current_section.dialogs.append(dialog)
    
    return report

def generate_markdown_report(report: TestReport) -> str:
    md = []
    
    # Header
    md.append("# Test Run Report\n")
    
    # Configuration
    md.append("## Configuration\n")
    for key, value in report.config.items():
        md.append(f"- **{key}:** {value}")
    md.append(f"- **Duration:** {(report.end_time - report.start_time).total_seconds():.1f} seconds\n")
    
    # Summary
    md.append("## Summary\n")
    total_dialogs = sum(len(section.dialogs) for section in report.sections)
    md.append(f"- **Total Interactions:** {total_dialogs}")
    md.append(f"- **Test Sections:** {len(report.sections)}\n")
    
    # Enhanced section reporting
    for section in report.sections:
        md.append(f"## {section.name}\n")
        md.append(f"{section.description}\n")
        
        # Track section statistics
        total_tests = 0
        passed_tests = 0
        
        for dialog in section.dialogs:
            md.append("### Dialog Exchange\n")
            
            # Show conversation flow
            if "conversation" in dialog:
                for msg in dialog["conversation"]:
                    md.append(f"**{msg['speaker']}:** {msg['message']}\n")
            
            # Show agent response and reasoning
            if "agent_response" in dialog:
                md.append(f"**Agent:** {dialog['agent_response']}\n")
            if "reasoning" in dialog:
                md.append(f"**Internal Reasoning:** {dialog['reasoning']}\n")
            
            # Show evaluations
            if "evaluation" in dialog:
                md.append("\n**Response Evaluation:**")
                for key, value in dialog["evaluation"].items():
                    if key != "explanation":
                        md.append(f"- ✓ **{key}:** {value}")
                if "explanation" in dialog["evaluation"]:
                    md.append(f"\n*{dialog['evaluation']['explanation']}*")
            
            # Show test results
            if "test_results" in dialog:
                md.append("\n**Test Results:**")
                for result in dialog["test_results"]:
                    md.append(f"- {result}")
                    total_tests += 1
                    if result.startswith("✓"):
                        passed_tests += 1
            
            md.append("\n---\n")
        
        # Add section summary
        if total_tests > 0:
            success_rate = (passed_tests / total_tests) * 100
            md.append(f"\n**Section Summary:**")
            md.append(f"- Tests Run: {total_tests}")
            md.append(f"- Tests Passed: {passed_tests}")
            md.append(f"- Success Rate: {success_rate:.1f}%\n")
    
    return "\n".join(md)

def generate_report_from_logs(log_dir: str, log_file: Optional[str] = None, output_format: str = "md"):
    if log_file:
        log_path = os.path.join(log_dir, log_file)
    else:
        # Find most recent log
        log_files = [f for f in os.listdir(log_dir) if f.endswith('.log')]
        if not log_files:
            raise ValueError(f"No log files found in {log_dir}")
        log_file = max(log_files, key=lambda x: os.path.getctime(os.path.join(log_dir, x)))
        log_path = os.path.join(log_dir, log_file)
    
    # Parse log and generate report
    report = parse_log_file(log_path)
    
    if output_format == "md":
        output = generate_markdown_report(report)
        output_file = log_path.replace(".log", "_report.md")
    else:
        raise ValueError(f"Unsupported output format: {output_format}")
    
    with open(output_file, 'w') as f:
        f.write(output)
    
    print(f"Report generated: {output_file}")

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--format",
        choices=["md", "docx"],
        default="md",
        help="Output format for report"
    )
    parser.add_argument(
        "--log-dir",
        default="test_logs",
        help="Directory containing test logs"
    )
    parser.add_argument(
        "--log-file",
        help="Specific log file to generate report from (optional)"
    )
    parser.add_argument(
        "--latest",
        action="store_true",
        help="Use only the most recent log file"
    )
    args = parser.parse_args()
    
    if args.log_file:
        # Use specific file
        if not os.path.exists(args.log_file):
            print(f"Error: Log file not found: {args.log_file}")
            return
        generate_report_from_logs(
            log_dir=os.path.dirname(args.log_file),
            log_file=os.path.basename(args.log_file),
            output_format=args.format
        )
    elif args.latest:
        # Find most recent log file
        log_files = [f for f in os.listdir(args.log_dir) if f.endswith('.log')]
        if not log_files:
            print(f"No log files found in {args.log_dir}")
            return
        latest_file = max(log_files, key=lambda x: os.path.getctime(os.path.join(args.log_dir, x)))
        generate_report_from_logs(
            log_dir=args.log_dir,
            log_file=latest_file,
            output_format=args.format
        )
    else:
        # Use all files in directory
        generate_report_from_logs(
            log_dir=args.log_dir,
            output_format=args.format
        )

if __name__ == "__main__":
    main() 