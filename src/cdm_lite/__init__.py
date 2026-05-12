from pathlib import Path

from cdm_models.cdm_event_common_TradeState_schema import TradeState

EXAMPLES = Path("src/fpml-confirmation-to-trade-state/")


def main():

    assert EXAMPLES.is_dir()

    successes, failures = [], []
    files = EXAMPLES.glob("**/*.json")
    for file in files:
        try:
            with file.open() as f:
                trade_json = f.read()
                _ = TradeState.model_validate_json(trade_json)
                successes.append(file.name)

        except Exception as err:
            failures.append((file.name, err))

    print(f"Deserialized Ok : {len(successes)}")
    print(f"Failed          : {len(failures)}")

    # for name, err in failures:
    #     print(f"  {name}: {err}")
