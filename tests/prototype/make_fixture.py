"""Small deterministic registration fixture, not a biological benchmark."""
from pathlib import Path
import numpy as np
import tifffile

p = Path('testing/prototype-images')
p.mkdir(parents=True, exist_ok=True)
y, x = np.mgrid[:256, :256]
image = np.zeros((256, 256), dtype=float)
labels = np.zeros(image.shape, dtype=np.uint16)
rng = np.random.default_rng(7)
for index, (cy, cx, radius) in enumerate(rng.integers([20,20,3], [236,236,10], size=(55,3)), 1):
    d = (y-cy)**2+(x-cx)**2
    image += np.exp(-d/(2*radius**2))
    labels[d < radius**2] = index
image = (image/image.max()*255).astype('uint8')
meta = {'PhysicalSizeX':0.17,'PhysicalSizeY':0.17,'PhysicalSizeXUnit':'µm','PhysicalSizeYUnit':'µm'}
tifffile.imwrite(p/'fixed.ome.tif', np.stack([image]*4), metadata=dict(meta,axes='CYX'), photometric='minisblack')
tifffile.imwrite(p/'moving.ome.tif', np.stack([image]*3, axis=-1), metadata=dict(meta,axes='YXS'), photometric='rgb')
tifffile.imwrite(p/'mask.tif', labels, metadata={'axes':'YX'}, photometric='minisblack')
np.save(p/'identity.npy', np.eye(3))
(p/'metrics.json').write_text('{}')
(p/'markers.csv').write_text('marker_name\nDAPI\nMarker1\nMarker2\nMarker3\n')
print(p.resolve())
