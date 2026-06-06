"""WIP building-footprint blockout (throwaway TMP_ objects; never saves master).

Run inside the open HexBase.blend GUI session via the Blender MCP (exec the body).
NOT yet the production generator -- once signed off this folds into gen_street_tiles.py.

Requires Shapely in Blender's Python (installed 2026-06-05):
    "C:\\Program Files\\Blender Foundation\\Blender 5.1\\5.1\\python\\bin\\python.exe" -m pip install shapely

Contract recap (Source_Art/README.md): R=5 flat-top, apothem 4.33, 5 m edges,
carriageway 3 m, 1 m walk.

Building recipe (signed off this session):
  - footprint = hex MINUS center->edge road corridors (half-width KEEP_HW=2.5, i.e.
    building face 1 m behind the curb; the 1 m strip is the walk). Neighbours meet at
    the non-road hex edges.
  - morphological OPENING (Shapely buffer(-0.2).buffer(+0.2), mitred) erases every
    sliver thinner than 0.4 m -- this is what kills the flatiron blades cleanly.
  - hollow shell: 0.25 m walls, room void = piece.buffer(-0.25), doorway box-cut per
    street frontage.
  - wall (eaves) height 6 m default; a couple of tiles at 9 m for variety.
  - roof = OBB-GABLE: oriented bounding box -> ridge axis; a triangular "tent" prism
    (two planar slopes) INTERSECTED with the footprint volume so slopes clip exactly to
    plan (crisp gable ends, clean cuts at notches). PITCH 35 deg.

PERF LESSON (cost a Blender crash on a 32 GB box): never run bmesh.ops.inset_region
(use_even_offset) on concave footprints, and never run an EXACT boolean THROUGH
inset-collapse/self-intersecting roof geometry -- it balloons RAM and hangs. Order:
booleans on simple prism/tent solids only. The Shapely-first pipeline below has no such
risk (all booleans are simple-solid INTERSECT/DIFFERENCE).
"""

import bpy, bmesh, math
from shapely.geometry import Polygon
from shapely.ops import unary_union

R=5.0; TOP=0.5; PAVE_TOP=0.65; HW=1.5; INR=R*math.cos(math.radians(30))
EDGE_ANG={0:90,1:150,2:210,3:270,4:330,5:30}
WALK=1.0; KEEP_HW=HW+WALK; WALL_T=0.25; T0=-0.8; T1=6.0
OPEN_R=0.20; MIT=5.0; PITCH=35.0


def reset_tmp():
    for o in list(bpy.data.objects):
        if o.name.startswith("TMP_"): bpy.data.objects.remove(o, do_unlink=True)
    for me in list(bpy.data.meshes):
        if me.users == 0: bpy.data.meshes.remove(me)


# ---- footprint (Shapely) ----
def hexpoly():
    return Polygon([(R*math.cos(math.radians(60*i)), R*math.sin(math.radians(60*i))) for i in range(6)])

def corridor(e):
    a=math.radians(EDGE_ANG[e]); dx,dy=math.cos(a),math.sin(a); px,py=-dy,dx
    P=lambda t,s:(t*dx+s*px, t*dy+s*py)
    return Polygon([P(T0,-KEEP_HW),P(T1,-KEEP_HW),P(T1,KEEP_HW),P(T0,KEEP_HW)])

def footprint(edges):
    fp=hexpoly()
    if edges: fp=fp.difference(unary_union([corridor(e) for e in edges]))
    fp=fp.buffer(-OPEN_R, join_style=2, mitre_limit=MIT).buffer(OPEN_R, join_style=2, mitre_limit=MIT)
    if fp.is_empty: return []
    return [fp] if fp.geom_type=='Polygon' else [g for g in fp.geoms if g.geom_type=='Polygon']


# ---- mesh helpers ----
def prism(ring, z0, z1, name, mat=None):
    pts=list(ring.coords)[:-1]
    me=bpy.data.meshes.new(name); bm=bmesh.new()
    bot=[bm.verts.new((x,y,z0)) for (x,y) in pts]; top=[bm.verts.new((x,y,z1)) for (x,y) in pts]
    n=len(pts); bm.faces.new(list(reversed(bot))); bm.faces.new(top)
    for i in range(n):
        j=(i+1)%n; bm.faces.new([bot[i],bot[j],top[j],top[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new(name, me)
    if mat: o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o); return o

def _box(bm, ad, t0, t1, s0, s1, z0, z1):
    a=math.radians(ad); dx,dy=math.cos(a),math.sin(a); px,py=-dy,dx
    P=lambda t,s,z:(t*dx+s*px, t*dy+s*py, z)
    cs=[P(t0,s0,z0),P(t1,s0,z0),P(t1,s1,z0),P(t0,s1,z0),P(t0,s0,z1),P(t1,s0,z1),P(t1,s1,z1),P(t0,s1,z1)]
    vs=[bm.verts.new(c) for c in cs]
    for f in [(0,1,2,3),(7,6,5,4),(0,4,5,1),(1,5,6,2),(2,6,7,3),(3,7,4,0)]: bm.faces.new([vs[i] for i in f])

def keepout(name, edges, hw, z0, z1):
    me=bpy.data.meshes.new(name); bm=bmesh.new()
    for e in edges: _box(bm, EDGE_ANG[e], T0, T1, -hw, hw, z0, z1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

def doors(name, edges):
    me=bpy.data.meshes.new(name); bm=bmesh.new()
    for e in edges:
        for sgn in (1,-1): _box(bm, EDGE_ANG[e], 2.4, 3.7, sgn*2.30, sgn*2.95, PAVE_TOP, PAVE_TOP+2.1)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

def boolean(t, c, op):
    md=t.modifiers.new("b", 'BOOLEAN'); md.operation=op; md.object=c
    md.solver='EXACT'; md.use_self=True; md.use_hole_tolerant=True
    bpy.ops.object.select_all(action='DESELECT'); t.select_set(True); bpy.context.view_layer.objects.active=t
    bpy.ops.object.modifier_apply(modifier="b"); bpy.data.objects.remove(c, do_unlink=True)

def carve(t, c): boolean(t, c, 'DIFFERENCE')

def hexbase(name, z0, z1, mat, tag):
    me=bpy.data.meshes.new("TMP_%s_%s"%(name,tag)); bm=bmesh.new()
    ang=[math.radians(60*i) for i in range(6)]
    bot=[bm.verts.new((R*math.cos(a),R*math.sin(a),z0)) for a in ang]
    top=[bm.verts.new((R*math.cos(a),R*math.sin(a),z1)) for a in ang]
    bm.faces.new(list(reversed(bot))); bm.faces.new(top)
    for i in range(6):
        j=(i+1)%6; bm.faces.new([bot[i],bot[j],top[j],top[i]])
    bm.normal_update(); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new("TMP_%s_%s"%(name,tag), me); o.data.materials.append(mat)
    bpy.context.scene.collection.objects.link(o); return o


# ---- OBB gable roof ----
def obb_axes(piece):
    cs=list(piece.minimum_rotated_rectangle.exterior.coords)[:-1]
    sub=lambda a,b:(a[0]-b[0],a[1]-b[1]); ln=lambda a:math.hypot(a[0],a[1])
    e0=sub(cs[1],cs[0]); e1=sub(cs[2],cs[1]); l0=ln(e0); l1=ln(e1)
    cx=sum(p[0] for p in cs)/4; cy=sum(p[1] for p in cs)/4
    if l0>=l1: u=(e0[0]/l0,e0[1]/l0); L=l0/2; W=l1/2; v=(e1[0]/l1,e1[1]/l1)
    else:      u=(e1[0]/l1,e1[1]/l1); L=l1/2; W=l0/2; v=(e0[0]/l0,e0[1]/l0)
    return (cx,cy), u, v, L, W

def gable_tent(name, center, u, v, L, W, base_z, H):
    cx,cy=center; Lext=L+0.2
    wp=lambda xp,yp,z:(cx+u[0]*xp+v[0]*yp, cy+u[1]*xp+v[1]*yp, z)
    tri=[(-W,base_z),(W,base_z),(0.0,base_z+H)]
    me=bpy.data.meshes.new(name); bm=bmesh.new()
    A=[bm.verts.new(wp(-Lext,yp,z)) for (yp,z) in tri]
    B=[bm.verts.new(wp( Lext,yp,z)) for (yp,z) in tri]
    bm.faces.new(A); bm.faces.new(list(reversed(B)))
    for i in range(3):
        j=(i+1)%3; bm.faces.new([A[i],A[j],B[j],B[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(me); bm.free()
    o=bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o); return o

def roof(piece, base_z, name, mat):
    center,u,v,L,W=obb_axes(piece); H=W*math.tan(math.radians(PITCH))
    rp=prism(piece.exterior, base_z, base_z+H+1.0, name, mat)
    boolean(rp, gable_tent(name+"_t", center, u, v, L, W, base_z, H), 'INTERSECT')
    return rp


def build_tile(name, edges, origin, wall_h, mats):
    mg,mp,mr=mats
    wt=PAVE_TOP+wall_h; objs=[hexbase(name,0.0,TOP,mg,"base")]
    pave=hexbase(name,TOP,PAVE_TOP,mp,"pave")
    if edges: carve(pave, keepout("TMP_%s_rc"%name, edges, HW, 0.45, 0.75))
    objs.append(pave)
    for k,pc in enumerate(footprint(edges)):
        bld=prism(pc.exterior, PAVE_TOP, wt, "TMP_%s_bld%d"%(name,k), mp)
        inner=pc.buffer(-WALL_T, join_style=2, mitre_limit=MIT)
        if (not inner.is_empty) and inner.geom_type=='Polygon' and inner.area>0.4:
            carve(bld, prism(inner.exterior, PAVE_TOP+0.05, wt-0.25, "TMP_%s_void%d"%(name,k)))
        if edges: carve(bld, doors("TMP_%s_dr%d"%(name,k), edges))
        objs.append(bld)
        objs.append(roof(pc, wt, "TMP_%s_roof%d"%(name,k), mr))
    bpy.ops.object.select_all(action='DESELECT')
    for o in objs: o.select_set(True)
    bpy.context.view_layer.objects.active=objs[0]; bpy.ops.object.join()
    t=objs[0]; t.name="TMP_TILE_%s"%name; t.location=origin; return t


def main():
    reset_tmp()
    mats=(bpy.data.materials["M_HexGround"], bpy.data.materials["M_Pavement"], bpy.data.materials["M_Road"])
    SP=13.0
    layout=[("deadend",[0],(0,0),9.0), ("bend",[0,1],(SP,0),6.0), ("curve",[0,2],(2*SP,0),6.0),
            ("straight",[0,3],(0,-SP),6.0), ("tee",[0,2,4],(SP,-SP),9.0),
            ("junction",[0,1,2,3,4,5],(2*SP,-SP),6.0)]
    for nm,ed,(ox,oy),wh in layout:
        build_tile(nm, ed, (ox,oy,0.0), wh, mats)
    print("built", [o.name for o in bpy.data.objects if o.name.startswith("TMP_TILE")])


if __name__ == "__main__":
    main()
