# Rigid vehicle presentation motion

`axm_uc.rigid_vehicle_motion` compiles explicit vehicle presentation samples into reusable rigid transform traces for a body, four suspension/steering corners, and four wheels. The output can feed the sticker assembly exporter or another renderer without making that renderer the owner of gameplay state.

The caller owns distance, steering, suspension, body response, impact response, damage stage, and light state. The compiler validates bounds, derives wheel roll from distance and radius, restricts steering to the front corners, and retains non-transform presentation states in a sidecar. Samples must be dense enough that consecutive wheel rotations do not alias across more than π radians.

```bash
axm-assets vehicle-motion-compose request.json output-directory
```

This capability does not simulate tyres, solve suspension, infer contact, apply damage, or change gameplay state.
