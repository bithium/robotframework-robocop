""" General E2E tests to catch any general issue in robocop """
from pathlib import Path
import pytest
from robocop.exceptions import (
    FileError,
    ArgumentFileNotFoundError,
    NestedArgumentFileError,
    ConfigGeneralError,
)
from robocop.run import Robocop
from robocop.config import Config


@pytest.fixture
def robocop_instance():
    return Robocop(from_cli=True)


@pytest.fixture
def robocop_instance_not_cli():
    return Robocop(from_cli=False)


@pytest.fixture
def test_data_dir():
    return Path(Path(__file__).parent.parent, "test_data")


def should_run_with_config(robocop_instance, cfg):
    config = Config()
    config.parse_opts(cfg.split())
    robocop_instance.config = config
    with pytest.raises(SystemExit):
        robocop_instance.run()
    return robocop_instance


class TestE2E:
    def test_run_all_checkers(self, robocop_instance, test_data_dir):
        should_run_with_config(robocop_instance, str(test_data_dir))

    def test_run_all_checkers_not_cli(self, robocop_instance_not_cli, test_data_dir):
        robocop_instance_not_cli.config.paths = [str(test_data_dir)]
        issues = robocop_instance_not_cli.run()
        assert issues
        assert isinstance(issues[0], dict)

    def test_run_all_checkers_not_recursive(self, robocop_instance, test_data_dir):
        should_run_with_config(robocop_instance, f"--no-recursive {test_data_dir}")

    def test_all_reports(self, robocop_instance, test_data_dir):
        should_run_with_config(robocop_instance, f"-r all {test_data_dir}")

    def test_no_issues_all_reports(self, robocop_instance, test_data_dir):
        should_run_with_config(robocop_instance, f'-r all {test_data_dir / "all_passing.robot"}')

    def test_disable_all_pattern(self, robocop_instance, test_data_dir):
        should_run_with_config(robocop_instance, f"--exclude * {test_data_dir}")

    def test_ignore_file_with_pattern(self, robocop_instance, test_data_dir):
        should_run_with_config(robocop_instance, f"--ignore *.robot --include 0502 {test_data_dir}")

    def test_include_one_rule(self, robocop_instance, test_data_dir):
        should_run_with_config(robocop_instance, f"--include 0503 {test_data_dir}")

    def test_run_non_existing_file(self, robocop_instance):
        config = Config()
        config.parse_opts(["some_path"])
        robocop_instance.config = config
        with pytest.raises(FileError) as err:
            robocop_instance.run()
        assert 'File "some_path" does not exist' in str(err)

    def test_run_with_return_status_0(self, robocop_instance, test_data_dir):
        runner = should_run_with_config(robocop_instance, f"-c return_status:quality_gate:E=-1:W=-1 {test_data_dir}")
        assert runner.reports["return_status"].return_status == 0

    def test_run_with_return_status_bigger_than_zero(self, robocop_instance, test_data_dir):
        runner = should_run_with_config(
            robocop_instance,
            f"--configure return_status:quality_gate:E=0:W=0 {test_data_dir}",
        )
        assert runner.reports["return_status"].return_status > 0

    def test_configure_rule_severity(self, robocop_instance, test_data_dir):
        should_run_with_config(robocop_instance, f"-c 0201:severity:E -c E0202:severity:I {test_data_dir}")

    def test_configure_rule_option(self, robocop_instance, test_data_dir):
        should_run_with_config(robocop_instance, f"-c line-too-long:line_length:1000 {test_data_dir}")

    @pytest.mark.parametrize(
        "rule, expected",
        [
            ("idontexist", "Provided rule or report 'idontexist' does not exist."),
            (
                "not-enough-whitespace-after-newline-mark",
                r"Provided rule or report 'not-enough-whitespace-after-newline-mark' does not exist. "
                r"Did you mean:\n    not-enough-whitespace-after-newline-marker",
            ),
        ],
    )
    def test_configure_invalid_rule(self, robocop_instance, rule, expected, test_data_dir):
        config = Config()
        config.parse_opts(["--configure", f"{rule}:severity:E", str(test_data_dir)])
        robocop_instance.config = config
        robocop_instance.load_checkers()
        with pytest.raises(ConfigGeneralError) as err:
            robocop_instance.configure_checkers_or_reports()
        assert expected in str(err)

    @pytest.mark.parametrize(
        "rules, expected",
        [
            ("invalid", f"Provided rule 'invalid' does not exist."),
            ("parsing-error,invalid", "Provided rule 'invalid' does not exist."),
            (
                "line-toolong",
                r"Provided rule 'line-toolong' does not exist. Did you mean:\n    line-too-long",
            ),
        ],
    )
    def test_include_exclude_invalid_rule(self, robocop_instance, rules, expected):
        for method in ("--include", "--exclude"):
            config = Config()
            config.parse_opts([method, rules, "."])
            robocop_instance.config = config
            with pytest.raises(ConfigGeneralError) as err:
                robocop_instance.reload_config()
            assert expected in str(err)

    def test_configure_invalid_param(self, robocop_instance, test_data_dir):
        config = Config()
        config.parse_opts(["--configure", "0202:idontexist:E", str(test_data_dir)])
        robocop_instance.config = config
        robocop_instance.load_checkers()
        with pytest.raises(ConfigGeneralError) as err:
            robocop_instance.configure_checkers_or_reports()
        assert (
            r"Provided param 'idontexist' for rule '0202' does not exist. "
            r"Available configurable(s) for this rule:\n    severity" in str(err)
        )

    def test_configure_invalid_config(self, robocop_instance, test_data_dir):
        config = Config()
        config.parse_opts(["--configure", "0202:", str(test_data_dir)])
        robocop_instance.config = config
        robocop_instance.load_checkers()
        with pytest.raises(ConfigGeneralError) as err:
            robocop_instance.configure_checkers_or_reports()
        assert "Provided invalid config: '0202:' (general pattern: <rule>:<param>:<value>)" in str(err)

    def test_configure_return_status_invalid_value(self, robocop_instance, test_data_dir):
        should_run_with_config(
            robocop_instance,
            f"--configure return_status:quality_gate:E0 {test_data_dir}",
        )

    def test_configure_return_status_with_non_exist(self, robocop_instance):
        config = Config()
        config.parse_opts(["--configure", "return_status:smth:E=0:W=0", str(test_data_dir)])
        robocop_instance.config = config
        robocop_instance.load_reports()
        with pytest.raises(ConfigGeneralError) as err:
            robocop_instance.configure_checkers_or_reports()
        assert "Provided param 'smth' for report 'return_status' does not exist" in str(err)

    def test_use_argument_file(self, robocop_instance, test_data_dir):
        should_run_with_config(robocop_instance, f'-A {test_data_dir / "argument_file" / "args.txt"}')

    def test_use_not_existing_argument_file(self, test_data_dir):
        config = Config()
        with pytest.raises(ArgumentFileNotFoundError) as err:
            config.parse_opts(["--argumentfile", "some_file", str(test_data_dir)])
        assert 'Argument file "some_file" does not exist' in str(err)

    def test_argument_file_without_path(self):
        config = Config()
        with pytest.raises(ArgumentFileNotFoundError) as err:
            config.parse_opts(["--argumentfile"])
        assert 'Argument file "" does not exist' in str(err)

    def test_use_nested_argument_file(self, test_data_dir):
        config = Config()
        nested_args_path = str(test_data_dir / "argument_file" / "args_nested.txt")
        with pytest.raises(NestedArgumentFileError) as err:
            config.parse_opts(["-A", nested_args_path, str(test_data_dir)])
        assert "Nested argument file in " in str(err)

    def test_set_rule_threshold(self, robocop_instance, test_data_dir):
        should_run_with_config(robocop_instance, f"--threshold E {test_data_dir}")

    def test_set_rule_invalid_threshold(self, robocop_instance, test_data_dir):
        should_run_with_config(robocop_instance, f"--threshold 3 {test_data_dir}")

    def test_configure_severity(self, robocop_instance, test_data_dir):
        # issue 402
        should_run_with_config(
            robocop_instance,
            f"-c wrong-case-in-keyword-name:severity:E -c wrong-case-in-keyword-name:convention:first_word_capitalized"
            f"{test_data_dir}",
        )

    def test_diff_encoded_chars(self, robocop_instance, test_data_dir, capsys):
        # issue 455
        should_run_with_config(robocop_instance, str(test_data_dir / "encodings.robot"))
        out, _ = capsys.readouterr()
        assert "Failed to decode" not in out
