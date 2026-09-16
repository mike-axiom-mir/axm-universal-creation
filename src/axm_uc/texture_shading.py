"""Core metal/rough inspection shading, with explicit approximations.

Triangle-derived tangent frame, no MikkTSpace equivalence, image-based lighting,
anisotropic filtering or material-extension support is claimed.
"""
import math

from .native_textures import srgb_byte


def dot(a, b):
    return sum(x*y for x, y in zip(a, b))


def unit(a):
    length = math.sqrt(dot(a, a))
    return tuple(x/length for x in a) if length > 1e-12 else (0.0, 0.0, 1.0)


def prepare_face(points, uv, screen, bindings, normal):
    e1, e2 = ([points[j][i]-points[0][i] for i in range(3)] for j in (1, 2))
    du1, dv1 = uv[1][0]-uv[0][0], uv[1][1]-uv[0][1]
    du2, dv2 = uv[2][0]-uv[0][0], uv[2][1]-uv[0][1]
    determinant = du1*dv2-du2*dv1
    if abs(determinant) <= 1e-12:
        raise ValueError("texture preview cannot shade collapsed UV triangles")
    tangent = unit([(e1[i]*dv2-e2[i]*dv1)/determinant for i in range(3)])
    bitangent = unit([(e2[i]*du1-e1[i]*du2)/determinant for i in range(3)])
    dx1, dy1 = screen[1][0]-screen[0][0], screen[1][1]-screen[0][1]
    dx2, dy2 = screen[2][0]-screen[0][0], screen[2][1]-screen[0][1]
    determinant_screen = dx1*dy2-dx2*dy1
    du_dx, du_dy = (du1*dy2-du2*dy1)/determinant_screen, (du2*dx1-du1*dx2)/determinant_screen
    dv_dx, dv_dy = (dv1*dy2-dv2*dy1)/determinant_screen, (dv2*dx1-dv1*dx2)/determinant_screen
    lods = {}
    for name, binding in bindings.items():
        texture = binding["texture"]
        footprint = max(math.hypot(du_dx*texture.width, dv_dx*texture.height),
                        math.hypot(du_dy*texture.width, dv_dy*texture.height), 1)
        lods[name] = math.log2(footprint) if binding["mipmaps"] else 0
    return tangent, bitangent, lods


def shade_pixel(uv, bindings, frame, normal, base, metallic, roughness, emissive, forward, lamps, profile):
    tangent, bitangent, lods = frame
    samples = {name: info["texture"].sample(*uv, lods[name], info["wrap_s"], info["wrap_t"])
               for name, info in bindings.items()}
    if "base_color" in samples:
        base = [v*s for v, s in zip(base, samples["base_color"])]
    if "orm" in samples:
        roughness *= samples["orm"][1]
        metallic *= samples["orm"][2]
    roughness = max(.045, roughness)
    if "normal" in samples:
        n = [2*v-1 for v in samples["normal"]]
        n[0] *= bindings["normal"]["scale"]
        n[1] *= bindings["normal"]["scale"]
        normal = unit([tangent[i]*n[0]+bitangent[i]*n[1]+normal[i]*n[2] for i in range(3)])
    ao = 1.0
    if "ao" in samples:
        ao = 1 + bindings["ao"]["strength"]*(samples["ao"][0]-1)
    result = [base[c]*profile["ambient"][c]*ao for c in range(3)]
    ndotv = max(1e-5, dot(normal, forward))
    alpha2 = roughness ** 4
    k = (roughness+1)**2/8
    gv = ndotv/(ndotv*(1-k)+k)
    for lamp in lamps:
        ndotl = max(0, dot(normal, lamp["direction"]))
        if ndotl <= 0:
            continue
        half = lamp["half"]
        ndoth, vdoth = max(0, dot(normal, half)), max(0, dot(forward, half))
        distribution = alpha2/(math.pi*(ndoth*ndoth*(alpha2-1)+1)**2)
        geometry = gv*ndotl/(ndotl*(1-k)+k)
        for c in range(3):
            f0 = .04*(1-metallic)+base[c]*metallic
            fresnel = f0+(1-f0)*(1-vdoth)**5
            specular = distribution*geometry*fresnel/max(4*ndotv*ndotl, 1e-6)
            diffuse = (1-fresnel)*(1-metallic)*base[c]/math.pi
            result[c] += (diffuse+specular)*lamp["color"][c]*lamp["intensity"]*ndotl*math.pi
    return bytes(srgb_byte((result[c]+emissive[c]*profile["emissive_gain"])*profile["exposure"]) for c in range(3))
