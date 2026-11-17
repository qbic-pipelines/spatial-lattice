import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace
import tempfile
import unittest
from unittest.mock import patch
import os
import tarfile

spec = importlib.util.spec_from_file_location('adapter', Path(__file__).resolve().parents[2]/'bin/rami2d_provenance.py')
adapter = importlib.util.module_from_spec(spec)
spec.loader.exec_module(adapter)

class AdapterTests(unittest.TestCase):
    def pixels(self, x=.17, y=.17, unit='µm'):
        return SimpleNamespace(physical_size_x=x, physical_size_y=y,
            physical_size_x_unit=SimpleNamespace(value=unit), physical_size_y_unit=SimpleNamespace(value=unit))

    def test_calibration_units_and_mismatch(self):
        adapter.validate_calibration(self.pixels(170,170,'nm'), .17)
        for pixels in (None, self.pixels(y=.18), self.pixels(x=None), self.pixels(unit='unknown')):
            with self.subTest(pixels=pixels), self.assertRaises(ValueError):
                adapter.validate_calibration(pixels, .17)

    def test_reference_channel_validation(self):
        settings = dict(fixed_mpp=.17,moving_mpp=.17,fixed_channel=2,moving_channel='h')
        with patch.object(adapter, 'image_info', return_value=({'C':3,'Y':10,'X':10}, self.pixels())):
            adapter.validate('fixed','moving',settings)
            with self.assertRaises(ValueError):
                adapter.validate('fixed','moving',dict(settings,fixed_channel=3))
        with patch.object(adapter, 'image_info', return_value=({'C':1,'Y':10,'X':10}, self.pixels())):
            with self.assertRaises(ValueError):
                adapter.validate('fixed','moving',dict(settings,fixed_channel=0))

    def test_native_transform_archive_and_status(self):
        with tempfile.TemporaryDirectory() as directory:
            old = Path.cwd()
            try:
                os.chdir(directory)
                transforms=Path('maps');transforms.mkdir()
                (transforms/'trf_00.txt').write_text('(Transform "EulerTransform")')
                Path('run.log').write_text('test log')
                with patch.object(adapter,'version',return_value='test'):
                    adapter.export(transforms,{'scheme':1},'run.log')
                result=json.loads(Path('registration.json').read_text())
                self.assertEqual(result['alignment_quality'],'not_assessed')
                self.assertEqual(result['ngff_native_transform_conversion'],'not_implemented')
                self.assertEqual(len(result['transform_files'][0]['sha256']),64)
                with tarfile.open('transforms.tar') as archive:
                    self.assertEqual(archive.getnames(),['registration/qc/fullres_trf/trf_00.txt','registration.log'])
            finally:
                os.chdir(old)

    def test_no_transform_is_error(self):
        with tempfile.TemporaryDirectory() as directory, self.assertRaises(ValueError):
            adapter.export(directory,{},'missing.log')

if __name__ == '__main__':
    unittest.main()
