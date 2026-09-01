import threading

import pytest

from ledger import CreditLedger, InvalidCreditError


def test_applies_credit_once(ledger):
    result = ledger.apply_credit("evt-1", "acc-1", 1000)

    assert result.applied is True
    assert result.balance_cents == 1000
    assert ledger.balance("acc-1") == 1000


def test_different_events_accumulate(ledger):
    ledger.apply_credit("evt-1", "acc-1", 1000)
    ledger.apply_credit("evt-2", "acc-1", 250)

    assert ledger.balance("acc-1") == 1250


def test_accounts_are_independent(ledger):
    ledger.apply_credit("evt-1", "acc-1", 1000)
    ledger.apply_credit("evt-2", "acc-2", 700)

    assert ledger.balance("acc-1") == 1000
    assert ledger.balance("acc-2") == 700


def test_duplicate_event_is_applied_only_once(ledger):
    ledger.apply_credit("evt-1", "acc-1", 1000)
    result = ledger.apply_credit("evt-1", "acc-1", 1000)

    assert result.applied is False
    assert ledger.balance("acc-1") == 1000


def test_duplicate_event_is_ignored_after_restart(database_path):
    CreditLedger(database_path).apply_credit("evt-1", "acc-1", 1000)

    restarted = CreditLedger(database_path)
    result = restarted.apply_credit("evt-1", "acc-1", 1000)

    assert result.applied is False
    assert restarted.balance("acc-1") == 1000


def test_unknown_account_has_zero_balance(ledger):
    assert ledger.balance("acc-inexistente") == 0


def test_simultaneous_duplicate_event_is_applied_once(ledger):
    start = threading.Barrier(2)
    results = []

    def apply_credit():
        start.wait()
        results.append(ledger.apply_credit("evt-concurrente", "acc-1", 1000))

    threads = [threading.Thread(target=apply_credit) for _ in range(2)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sum(result.applied for result in results) == 1
    assert ledger.balance("acc-1") == 1000


def test_simultaneous_duplicate_event_across_instances_is_applied_once(database_path):
    ledgers = [CreditLedger(database_path), CreditLedger(database_path)]
    start = threading.Barrier(len(ledgers))
    results = []

    def apply_credit(ledger):
        start.wait()
        results.append(ledger.apply_credit("evt-multi-worker", "acc-1", 1000))

    threads = [
        threading.Thread(target=apply_credit, args=(ledger,)) for ledger in ledgers
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert len(results) == 2
    assert sum(result.applied for result in results) == 1
    assert ledgers[0].balance("acc-1") == 1000


def test_invalid_event_can_be_retried_after_correction(ledger):
    with pytest.raises(InvalidCreditError):
        ledger.apply_credit("evt-invalido", "acc-1", 0)

    result = ledger.apply_credit("evt-invalido", "acc-1", 1000)

    assert result.applied is True
    assert result.balance_cents == 1000
