import pytest

from havoc_monkey.core import HavocMonkey


def pytest_addoption(parser):
    parser.addoption(
        "--havoc-seed",
        action="store",
        type=int,
        default=42,
        help="Seed for havoc-monkey's random number generator.",
    )


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "havoc_monkey(attacks, health_check=None): run a havoc-monkey campaign "
        "for this test and report results.",
    )


@pytest.fixture
def havoc_monkey_instance(request):
    seed = request.config.getoption("--havoc-seed")
    return HavocMonkey(seed=seed)


@pytest.hookimpl(wrapper=True)
def pytest_runtest_makereport(item, call):
    result = yield

    if call.when != "call":
        return result

    if not item.get_closest_marker("havoc_monkey"):
        return result

    instance = item.funcargs.get("havoc_monkey_instance")
    if instance is None or instance.last_report is None:
        return result

    if result.failed:
        result.sections.append(
            ("havoc-monkey campaign report", str(instance.last_report))
        )

    return result
