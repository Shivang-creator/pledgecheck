#!/bin/sh
# Pledgecheck dispatcher. POSIX sh, no bashisms, stdlib-only Python underneath.
# Subcommands: test | gate | baseline | compare | killswitch | flowchart | all
set -e

DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

CMD="${1:-all}"
if [ "$#" -gt 0 ]; then shift; fi

run_test() {
    OUT_FILE="$(mktemp)"
    STATUS=0
    python3 -m unittest discover -s tests -v "$@" >"$OUT_FILE" 2>&1 || STATUS=$?
    cat "$OUT_FILE"
    COUNT="$(grep -o 'Ran [0-9]* test' "$OUT_FILE" | tail -1 | grep -o '[0-9]*')"
    rm -f "$OUT_FILE"
    if [ -n "$COUNT" ]; then
        echo "TESTS: $COUNT"
    fi
    return "$STATUS"
}

run_gate() {
    python3 harness/run_gate.py "$@"
}

run_baseline() {
    python3 harness/run_baseline.py "$@"
}

run_compare() {
    python3 harness/compare.py "$@"
}

run_killswitch() {
    python3 harness/killswitch.py "$@"
}

run_flowchart() {
    node ~/Projects/pit-crew/bin/browse.js \
        "file://$DIR/deliverables/flowchart.html" \
        "$DIR/deliverables/flowchart.png" \
        1200 800
}

case "$CMD" in
    test)
        run_test "$@"
        ;;
    gate)
        run_gate "$@"
        ;;
    baseline)
        run_baseline "$@"
        ;;
    compare)
        run_compare "$@"
        ;;
    killswitch)
        run_killswitch "$@"
        ;;
    flowchart)
        run_flowchart
        ;;
    all)
        run_test
        run_gate
        run_baseline
        run_compare
        run_flowchart
        run_killswitch
        ;;
    *)
        echo "unknown command: $CMD" >&2
        echo "usage: ./run.sh {test|gate|baseline|compare|killswitch|flowchart|all}" >&2
        exit 1
        ;;
esac
