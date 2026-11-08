import argparse
from pathlib import Path

from src.task1_os_inspector import collect_android_evidence
from src.task2_threading import run_threading_lab
from src.task3_runtime import run_runtime_lab
from src.task4_security import run_security_audit
from src.task5_power import run_power_lab
from src.task6_tracking import run_tracking_lab

def main():
    parser = argparse.ArgumentParser(description="ITA03-MP CO4 Part II mobile systems engineering lab")
    parser.add_argument("task", choices=["all", "task1", "task2", "task3", "task4", "task5", "task6"])
    args = parser.parse_args()
    Path("outputs").mkdir(exist_ok=True)

    actions = {
        "task1": collect_android_evidence,
        "task2": run_threading_lab,
        "task3": run_runtime_lab,
        "task4": run_security_audit,
        "task5": run_power_lab,
        "task6": run_tracking_lab,
    }
    selected = list(actions.values()) if args.task == "all" else [actions[args.task]]
    for action in selected:
        print("\n" + "=" * 78)
        action()
    print("\nCompleted. Review the outputs/ directory and retain your actual logs.")

if __name__ == "__main__":
    main()
