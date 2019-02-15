import vispy.plot as vp
from vispy import color
from vispy.util.filter import gaussian_filter
import numpy as np

z = np.random.normal(size=(250, 250), scale=200)
z[100, 100] += 50000
z = gaussian_filter(z, (10, 10))

fig = vp.Fig(show=False)
cnorm = z / abs(np.amax(z))
c = color.get_colormap("hsl").map(cnorm).reshape(z.shape + (-1,))
c = c.flatten().tolist()
c=list(map(lambda x,y,z,w:(x,y,z,w), c[0::4],c[1::4],c[2::4],c[3::4]))

#p1 = fig[0, 0].surface(z, vertex_colors=c) # why doesn't vertex_colors=c work?
p1 = fig[0, 0].surface(z)
p1.mesh_data.set_vertex_colors(c) # but explicitly setting vertex colors does work?

fig.show()