"""Headless procedural transparent PNG example; run with Blender, not CPython."""

import argparse
from pathlib import Path
import math
import sys

import bpy
from mathutils import Vector


def material(name, color, metallic, roughness):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    p = m.node_tree.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = (*color,1)
    p.inputs["Metallic"].default_value = metallic
    p.inputs["Roughness"].default_value = roughness
    return m


def point(obj, target=(0,0,0)):
    obj.rotation_euler = (Vector(target) - obj.location).to_track_quat("-Z","Y").to_euler()


def build(args):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    s = bpy.context.scene
    s.render.engine = "CYCLES"
    s.cycles.device = "CPU"
    s.cycles.samples = 12
    s.cycles.use_denoising = True
    s.render.threads_mode = "FIXED"
    s.render.threads = 6
    s.render.film_transparent = True
    s.render.resolution_x,s.render.resolution_y = args.width,args.height
    s.render.resolution_percentage = 100
    s.render.image_settings.file_format = "PNG"
    s.render.image_settings.color_mode = "RGBA"
    s.render.fps = args.fps
    s.frame_start,s.frame_end = 0,args.frames-1
    s.render.filepath = str(args.out.resolve()) + "/"
    s.world = bpy.data.worlds.new("Neutral environment")
    s.world.color = (.16,.16,.16)
    bpy.ops.object.camera_add(location=(3.2,-6,3.0))
    cam = bpy.context.object
    point(cam)
    cam.data.type = "ORTHO"
    cam.data.ortho_scale = 5.6
    s.camera = cam

    for position,energy,color,radius in [
        ((3,-4,4),650,(1,.72,.47),4),((-3,-2,2),440,(.36,.8,1),3),((0,3,4),780,(.45,1,.79),3)
    ]:
        bpy.ops.object.light_add(type="AREA",location=position)
        light = bpy.context.object
        light.data.energy,light.data.color,light.data.size = energy,color,radius
        point(light)

    bpy.ops.object.empty_add()
    root = bpy.context.object
    teal = material("Sea glass",(.035,.51,.5),.38,.27)
    brass = material("Brass",(.83,.37,.08),.72,.31)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=1,radius=.82)
    bpy.context.object.scale = (.75,.75,1.25)
    bpy.context.object.data.materials.append(teal)
    bpy.context.object.parent = root
    for degrees in (39,-62):
        bpy.ops.mesh.primitive_torus_add(major_radius=1.05,minor_radius=.038,
                                       major_segments=48,minor_segments=12,
                                       rotation=(math.radians(degrees),.25,0))
        bpy.context.object.data.materials.append(brass)
        bpy.context.object.parent = root
        for poly in bpy.context.object.data.polygons:
            poly.use_smooth = True
    root.rotation_euler.z = 0
    root.keyframe_insert(data_path="rotation_euler",frame=0)
    root.rotation_euler.z = math.tau
    root.keyframe_insert(data_path="rotation_euler",frame=args.frames)
    for fcurve in root.animation_data.action.fcurves:
        for key in fcurve.keyframe_points:
            key.interpolation = "LINEAR"
    bpy.ops.render.render(animation=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--width",type=int,default=480)
    parser.add_argument("--height",type=int,default=270)
    parser.add_argument("--fps",type=int,default=16)
    parser.add_argument("--frames",type=int,default=32)
    args = parser.parse_args(sys.argv[sys.argv.index("--")+1:])
    if min(args.width,args.height,args.fps,args.frames) <= 0:
        parser.error("dimensions, fps, and frames must be positive")
    args.out.mkdir(parents=True,exist_ok=True)
    build(args)
