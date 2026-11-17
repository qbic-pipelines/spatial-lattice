"""Unit checks; Transformix comparison is in validate_rami2d_rfc5.py."""
import sys
from pathlib import Path
import unittest
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parents[2]/'bin'))
from rami2d_rfc5 import linear_matrix, compose_chain, parse_parameters


def parameters(kind, values, center=(0,0), parent='NoInitialTransform'):
    return dict(Transform=[kind], TransformParameters=list(map(str,values)),
                CenterOfRotationPoint=list(map(str,center)), FixedImageDimension=['2'],
                MovingImageDimension=['2'], HowToCombineTransforms=['Compose'],
                InitialTransformParameterFileName=[parent])


class TransformTests(unittest.TestCase):
    def test_centered_affine(self):
        matrix=linear_matrix(parameters('AffineTransform',[2,0.2,0,3,4,5],(7,11)))
        np.testing.assert_allclose(matrix@np.array([7,11,1]),[11,16,1])

    def test_link_order_not_file_order(self):
        maps={'z.txt':parameters('TranslationTransform',[4,5]),
              'a.txt':parameters('EulerTransform',[np.pi/2,0,0],parent='z.txt')}
        matrix,_,order=compose_chain(maps)
        self.assertEqual(order,['z.txt','a.txt'])
        np.testing.assert_allclose(matrix@np.array([1,2,1]),[-7,5,1],atol=1e-12)

    def test_reject_unsupported_and_singular(self):
        for p in [parameters('BSplineTransform',[1,2]),parameters('AffineTransform',[0,0,0,0,1,2]),
                  dict(parameters('TranslationTransform',[1,2]),HowToCombineTransforms=['Add'])]:
            with self.subTest(p=p), self.assertRaises(ValueError): linear_matrix(p)

    def test_bad_chains(self):
        for maps in [{'a':parameters('TranslationTransform',[0,0],parent='missing')},
                     {'a':parameters('TranslationTransform',[0,0],parent='b'), 'b':parameters('TranslationTransform',[0,0],parent='a')},
                     {'a':parameters('TranslationTransform',[0,0]), 'b':parameters('TranslationTransform',[0,0])}]:
            with self.subTest(maps=maps), self.assertRaises(ValueError): compose_chain(maps)

    def test_duplicate_parameter(self):
        with self.assertRaises(ValueError): parse_parameters('(Transform "EulerTransform")\n(Transform "AffineTransform")')

if __name__=='__main__': unittest.main()
