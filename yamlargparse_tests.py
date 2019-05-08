#!/usr/bin/env python
"""Unit tests for the yamlargparse module."""

import os
import sys
import shutil
import tempfile
import unittest
from yamlargparse import ArgumentParser, ActionYesNo, ActionConfigFile, ActionPath, ActionOperators, ArgumentTypeError, ArgumentError


def example_parser():
    """Creates a simple parser for doing tests."""
    parser = ArgumentParser(prog='app')

    group_one = parser.add_argument_group('Group 1', name='group1')
    group_one.add_argument('--bools.def_false',
        default=False,
        action=ActionYesNo)
    group_one.add_argument('--bools.def_true',
        default=True,
        action=ActionYesNo)

    group_two = parser.add_argument_group('Group 2', name='group2')
    group_two.add_argument('--lev1.lev2.opt1',
        default='opt1_def')
    group_two.add_argument('--lev1.lev2.opt2',
        default='opt2_def')

    group_three = parser.add_argument_group('Group 3')
    group_three.add_argument('--nums.val1',
        type=int,
        default=1)
    group_three.add_argument('--nums.val2',
        type=float,
        default=2.0)

    return parser


example_yaml = '''
lev1:
  lev2:
    opt1: opt1_yaml
    opt2: opt2_yaml

nums:
  val1: -1
  val2: -2.0
'''

example_env = {
    'APP_LEV1__LEV2__OPT1': 'opt1_env',
    'APP_NUMS__VAL1': '0'
}


class YamlargparseTests(unittest.TestCase):
    """Tests for yamlargparse."""

    def test_groups(self):
        """Test storage of named groups."""
        parser = example_parser()
        self.assertEqual(['group1', 'group2'], list(sorted(parser.groups.keys())))


    def test_parse_args(self):
        parser = example_parser()
        self.assertEqual('opt1_arg', parser.parse_args(['--lev1.lev2.opt1', 'opt1_arg']).lev1.lev2.opt1)
        self.assertEqual(9, parser.parse_args(['--nums.val1', '9']).nums.val1)
        self.assertEqual(6.4, parser.parse_args(['--nums.val2', '6.4']).nums.val2)
        #self.assertRaises(ArgumentError, lambda: parser.parse_args(['--nums.val1', '7.5']))
        #self.assertRaises(ArgumentError, lambda: parser.parse_args(['--nums.val2', 'str']))


    def test_yes_no_action(self):
        """Test the correct functioning of ActionYesNo."""
        parser = example_parser()
        defaults = parser.get_defaults()
        self.assertEqual(False, defaults.bools.def_false)
        self.assertEqual(True,  defaults.bools.def_true)
        self.assertEqual(True,  parser.parse_args(['--bools.def_false']).bools.def_false)
        self.assertEqual(False, parser.parse_args(['--no_bools.def_false']).bools.def_false)
        self.assertEqual(True,  parser.parse_args(['--bools.def_true']).bools.def_true)
        self.assertEqual(False, parser.parse_args(['--no_bools.def_true']).bools.def_true)


    def test_parse_yaml(self):
        """Test the parsing and checking of yaml."""
        parser = example_parser()

        cfg1 = parser.parse_yaml_string(example_yaml)
        self.assertEqual('opt1_yaml', cfg1.lev1.lev2.opt1)
        self.assertEqual('opt2_yaml', cfg1.lev1.lev2.opt2)
        self.assertEqual(-1,   cfg1.nums.val1)
        self.assertEqual(-2.0, cfg1.nums.val2)
        self.assertEqual(False, cfg1.bools.def_false)
        self.assertEqual(True,  cfg1.bools.def_true)

        cfg2 = parser.parse_yaml_string(example_yaml, defaults=False)
        self.assertFalse(hasattr(cfg2, 'bools'))
        self.assertTrue(hasattr(cfg2, 'nums'))

        tmpdir = tempfile.mkdtemp(prefix='_yamlargparse_tests_')
        yaml_file = os.path.realpath(os.path.join(tmpdir, 'example.yaml'))
        with open(yaml_file, 'w') as output_file:
            output_file.write(example_yaml)
        self.assertEqual(cfg1, parser.parse_yaml_path(yaml_file, defaults=True))
        self.assertEqual(cfg2, parser.parse_yaml_path(yaml_file, defaults=False))
        self.assertNotEqual(cfg2, parser.parse_yaml_path(yaml_file, defaults=True))
        self.assertNotEqual(cfg1, parser.parse_yaml_path(yaml_file, defaults=False))
        shutil.rmtree(tmpdir)


    def test_parse_env(self):
        """Test the parsing of environment variables."""
        parser = example_parser()
        cfg = parser.parse_env(env=example_env)
        self.assertEqual('opt1_env', cfg.lev1.lev2.opt1)
        self.assertEqual(0, cfg.nums.val1)
        cfg = parser.parse_env(env=example_env, defaults=False)
        self.assertFalse(hasattr(cfg, 'bools'))
        self.assertTrue(hasattr(cfg, 'nums'))


    def test_configfile_filepath(self):
        """Test the use of ActionConfigFile and ActionPath."""
        tmpdir = tempfile.mkdtemp(prefix='_yamlargparse_tests_')
        os.mkdir(os.path.join(tmpdir, 'example'))
        rel_yaml_file = os.path.join('..', 'example', 'example.yaml')
        abs_yaml_file = os.path.realpath(os.path.join(tmpdir, 'example', rel_yaml_file))
        with open(abs_yaml_file, 'w') as output_file:
            output_file.write('file: '+rel_yaml_file+'\ndir: '+tmpdir+'\n')

        parser = ArgumentParser(prog='app')
        parser.add_argument('--cfg',
            action=ActionConfigFile)
        parser.add_argument('--file',
            action=ActionPath(mode='r'))
        parser.add_argument('--dir',
            action=ActionPath(mode='drw'))

        cfg = parser.parse_args(['--cfg', abs_yaml_file])
        self.assertEqual(tmpdir, os.path.realpath(cfg.dir(absolute=True)))
        self.assertEqual(abs_yaml_file, os.path.realpath(cfg.cfg[0](absolute=False)))
        self.assertEqual(abs_yaml_file, os.path.realpath(cfg.cfg[0](absolute=True)))
        self.assertEqual(rel_yaml_file, cfg.file(absolute=False))
        self.assertEqual(abs_yaml_file, os.path.realpath(cfg.file(absolute=True)))
        self.assertRaises(ArgumentTypeError, lambda: parser.parse_args(['--cfg', abs_yaml_file+'~']))

        cfg = parser.parse_args(['--file', abs_yaml_file, '--dir', tmpdir])
        self.assertEqual(tmpdir, os.path.realpath(cfg.dir(absolute=True)))
        self.assertEqual(abs_yaml_file, os.path.realpath(cfg.file(absolute=True)))
        self.assertRaises(ArgumentTypeError, lambda: parser.parse_args(['--dir', abs_yaml_file]))
        self.assertRaises(ArgumentTypeError, lambda: parser.parse_args(['--file', tmpdir]))

        self.assertRaises(Exception, lambda: parser.add_argument('--op1', action=ActionPath))
        self.assertRaises(Exception, lambda: parser.add_argument('--op2', action=ActionPath()))
        self.assertRaises(Exception, lambda: parser.add_argument('--op3', action=ActionPath(mode='+')))

        shutil.rmtree(tmpdir)


    def test_operators(self):
        """Test the use of ActionOperators."""
        parser = ArgumentParser(prog='app')
        parser.add_argument('--le0',
            action=ActionOperators(expr=('<', 0)))
        parser.add_argument('--gt1.a.le4',
            action=ActionOperators(expr=[('>', 1.0), ('<=', 4.0)], join='and', numtype=float))
        parser.add_argument('--lt5.o.ge10.o.eq7',
            action=ActionOperators(expr=[('<', 5), ('>=', 10), ('==', 7)], join='or', numtype=int))

        self.assertEqual(1.5, parser.parse_args(['--gt1.a.le4', '1.5']).gt1.a.le4)
        self.assertEqual(4.0, parser.parse_args(['--gt1.a.le4', '4.0']).gt1.a.le4)
        self.assertRaises(ArgumentTypeError, lambda: parser.parse_args(['--gt1.a.le4', '1.0']))
        self.assertRaises(ArgumentTypeError, lambda: parser.parse_args(['--gt1.a.le4', '5.5']))

        self.assertEqual(1.5, parser.parse_yaml_string('gt1:\n  a:\n    le4: 1.5').gt1.a.le4)
        self.assertEqual(4.0, parser.parse_yaml_string('gt1:\n  a:\n    le4: 4.0').gt1.a.le4)
        self.assertRaises(ArgumentTypeError, lambda: parser.parse_yaml_string('gt1:\n  a:\n    le4: 1.0'))
        self.assertRaises(ArgumentTypeError, lambda: parser.parse_yaml_string('gt1:\n  a:\n    le4: 5.5'))

        self.assertEqual(1.5, parser.parse_env(env={'APP_GT1__A__LE4': '1.5'}).gt1.a.le4)
        self.assertEqual(4.0, parser.parse_env(env={'APP_GT1__A__LE4': '4.0'}).gt1.a.le4)
        self.assertRaises(ArgumentTypeError, lambda: parser.parse_env(env={'APP_GT1__A__LE4': '1.0'}))
        self.assertRaises(ArgumentTypeError, lambda: parser.parse_env(env={'APP_GT1__A__LE4': '5.5'}))

        self.assertEqual(2, parser.parse_args(['--lt5.o.ge10.o.eq7', '2']).lt5.o.ge10.o.eq7)
        self.assertEqual(7, parser.parse_args(['--lt5.o.ge10.o.eq7', '7']).lt5.o.ge10.o.eq7)
        self.assertEqual(10, parser.parse_args(['--lt5.o.ge10.o.eq7', '10']).lt5.o.ge10.o.eq7)
        self.assertRaises(ArgumentTypeError, lambda: parser.parse_args(['--lt5.o.ge10.o.eq7', '5']))
        self.assertRaises(ArgumentTypeError, lambda: parser.parse_args(['--lt5.o.ge10.o.eq7', '8']))

        self.assertRaises(Exception, lambda: parser.add_argument('--op1', action=ActionOperators))
        self.assertRaises(Exception, lambda: parser.add_argument('--op2', action=ActionOperators()))
        self.assertRaises(Exception, lambda: parser.add_argument('--op3', action=ActionOperators(expr='<')))


if __name__ == '__main__':
    unittest.main(verbosity=2)