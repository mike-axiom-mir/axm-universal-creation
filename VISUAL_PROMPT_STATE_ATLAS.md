# AXM Visual Prompt State Atlas

This table normalizes the 99 slash-command terms visible in the user-supplied **AI Prompts Compass** reference images received on 2026-09-01.

The source graphics are not redistributed. Their creator/owner and license were not supplied beyond the displayed source label. Definitions below are paraphrased. Every mapping remains a working hypothesis until an actual artifact supports it.

These commands are not magic. They are human shorthand for proposed visual state changes. The detailed state patches, overlaps, cautions, provenance, blend rules, and conflicts live in the machine-readable JSON files under `src/axm_uc/data/visual_state/`.

| # | Command | Category | Mapping | Normalized human meaning |
|---:|---|---|---|---|
| 1 | `/4k` | quality | output hint | Request a detailed output around a 4K delivery tier. |
| 2 | `/8k` | quality | output hint | Request an ultra-high-resolution, highly detailed output. |
| 3 | `/hdreal` | quality | interpretive | Bias the result toward polished high-definition photorealism. |
| 4 | `/ultrarealistic` | quality | interpretive | Push the visible treatment toward extreme photorealism. |
| 5 | `/cinematic` | style-lighting | composite bundle | Use film-like composition, lighting, and mood. |
| 6 | `/droneview` | camera | direct | Use an elevated aerial viewpoint resembling a drone shot. |
| 7 | `/aerialview` | camera | direct | Observe the scene from a high altitude above it. |
| 8 | `/topdown` | camera | direct | Point the camera directly downward from above. |
| 9 | `/lowangle` | camera | direct | Place the camera below the subject and look upward. |
| 10 | `/highangle` | camera | direct | Place the camera above the subject and look downward. |
| 11 | `/sideview` | camera | direct | Show the subject mainly from its side or profile. |
| 12 | `/closeup` | framing | direct | Frame the subject closely so it dominates the image. |
| 13 | `/extremecloseup` | framing | direct | Frame a very small part of the subject at extreme detail. |
| 14 | `/wideangle` | camera-lens | direct | Use a wide field of view that includes more of the environment. |
| 15 | `/fisheye` | camera-lens | direct | Use an ultra-wide fisheye projection with visible distortion. |
| 16 | `/pov` | camera | direct | Use a first-person viewpoint from the observer or character. |
| 17 | `/overtheshoulder` | camera | direct | View the scene from behind a subject's shoulder. |
| 18 | `/birdseyeview` | camera | direct | Show the scene from directly overhead at substantial height. |
| 19 | `/wormseyeview` | camera | direct | Use an extreme ground-level view looking vertically upward. |
| 20 | `/fog` | atmosphere | direct | Surround the scene with dense atmospheric fog. |
| 21 | `/mist` | atmosphere | direct | Add a lighter, softer mist to the scene. |
| 22 | `/rainynight` | environment-lighting | composite bundle | Combine rain with a nighttime environment. |
| 23 | `/rain` | weather | direct | Add rainfall, wet air, and wet surfaces. |
| 24 | `/storm` | weather | composite bundle | Create dramatic storm conditions with reduced visibility and charged lighting. |
| 25 | `/snow` | weather | direct | Add snowfall and a winter atmosphere. |
| 26 | `/sunset` | time-lighting | direct | Use warm late-day sunset illumination. |
| 27 | `/sunrise` | time-lighting | direct | Use soft early-morning sunrise illumination. |
| 28 | `/goldenhour` | time-lighting | direct | Use warm, low-angle golden-hour illumination. |
| 29 | `/bluehour` | time-lighting | direct | Use cool blue twilight illumination. |
| 30 | `/moonlight` | time-lighting | direct | Illuminate the scene primarily with moonlight. |
| 31 | `/neonlights` | lighting | direct | Use bright colored neon sources and glow. |
| 32 | `/cyberpunk` | world-style | composite bundle | Use a futuristic, dense, neon-lit cyberpunk visual language. |
| 33 | `/darkmoody` | style-lighting | composite bundle | Use low-key, dark, dramatic mood and contrast. |
| 34 | `/softlighting` | lighting | direct | Use gentle, diffuse illumination with soft shadows. |
| 35 | `/dramaticlighting` | lighting | direct | Use strong directional light and high contrast. |
| 36 | `/rimlight` | lighting | direct | Add a bright edge light around the subject. |
| 37 | `/backlight` | lighting | direct | Illuminate the subject from behind. |
| 38 | `/volumetriclight` | lighting | direct | Make light beams visible through participating atmosphere. |
| 39 | `/godrays` | lighting | composite bundle | Use dramatic shafts of light through clouds, dust, or atmosphere. |
| 40 | `/studio` | environment-lighting | composite bundle | Use a controlled professional studio setup. |
| 41 | `/filmgrain` | postprocess | direct | Add analog-style film grain. |
| 42 | `/anamorphic` | camera-lens | direct | Use a widescreen anamorphic lens treatment. |
| 43 | `/bokeh` | depth | direct | Render out-of-focus highlights as soft background shapes. |
| 44 | `/shallowdepth` | depth | direct | Keep the subject sharp while strongly blurring background depth. |
| 45 | `/motionblur` | motion | direct | Blur moving elements to communicate dynamic motion. |
| 46 | `/longexposure` | motion-photography | direct | Accumulate motion across a long simulated exposure. |
| 47 | `/freezeaction` | motion | direct | Capture fast movement sharply with minimal motion trail. |
| 48 | `/vintage` | style | interpretive | Use an aged photographic or design treatment. |
| 49 | `/retro` | style | interpretive | Use a nostalgic retro-inspired visual treatment. |
| 50 | `/oldmoney` | style | interpretive | Use restrained, traditional, inherited-luxury visual cues. |
| 51 | `/luxury` | style | interpretive | Use premium, refined, high-end visual treatment. |
| 52 | `/minimalist` | style | direct + interpretive | Use sparse composition and reduced visual complexity. |
| 53 | `/editorial` | style | interpretive | Use professional magazine-editorial composition. |
| 54 | `/fashion` | style | interpretive | Use a high-fashion photography or presentation language. |
| 55 | `/streetstyle` | style-environment | composite bundle | Use a contemporary urban street-fashion treatment. |
| 56 | `/magazinecover` | format | composite bundle | Compose the image as a professional magazine cover. |
| 57 | `/polaroid` | format-photography | composite bundle | Use an instant-film print frame and Polaroid-like look. |
| 58 | `/disposablecamera` | photography | composite bundle | Use a raw disposable-camera snapshot treatment. |
| 59 | `/35mmfilm` | photography | composite bundle | Use a classic 35 mm analog-film treatment. |
| 60 | `/instantphoto` | format-photography | composite bundle | Use a generic instant-camera photo appearance. |
| 61 | `/underwater` | environment | composite bundle | Place the scene below the water surface. |
| 62 | `/space` | environment | direct + interpretive | Place the scene in outer space or a cosmic environment. |
| 63 | `/desert` | environment | direct | Place the scene in a desert landscape. |
| 64 | `/forest` | environment | direct | Place the scene in a natural forest. |
| 65 | `/mountains` | environment | direct | Place the scene in a dramatic mountain landscape. |
| 66 | `/beach` | environment | direct | Place the scene in a coastal or beach environment. |
| 67 | `/cityscape` | environment | direct | Use an urban skyline or city landscape as the setting. |
| 68 | `/nightcity` | environment-time | composite bundle | Use a city environment at night. |
| 69 | `/futuristic` | world-style | interpretive | Use advanced future-oriented visual design. |
| 70 | `/postapocalyptic` | world-style | composite bundle | Use a ruined, dystopian, post-collapse world treatment. |
| 71 | `/fantasy` | world-style | composite bundle | Use a magical and imaginative fantasy-world treatment. |
| 72 | `/scifi` | world-style | interpretive | Use a science-fiction inspired visual language. |
| 73 | `/medieval` | world-style | composite bundle | Use a historical medieval-era visual language. |
| 74 | `/samurai` | world-style | interpretive | Use a cinematic original scene inspired by historical samurai visual language. |
| 75 | `/noir` | world-style | composite bundle | Use dark, high-contrast film-noir visual language. |
| 76 | `/detective` | world-style | interpretive | Use a mystery and detective-inspired atmosphere. |
| 77 | `/superhero` | world-style | interpretive | Use an epic visual language for an original heroic comic archetype. |
| 78 | `/anime` | art-medium | interpretive | Use a broad Japanese animation-inspired illustration treatment. |
| 79 | `/comicbook` | art-medium | composite bundle | Use an illustrated comic-book treatment. |
| 80 | `/oilpainting` | art-medium | direct + interpretive | Use a traditional oil-painting treatment. |
| 81 | `/watercolor` | art-medium | composite bundle | Use a soft watercolor painting treatment. |
| 82 | `/sketch` | art-medium | composite bundle | Use a hand-drawn sketch treatment. |
| 83 | `/claystyle` | art-medium | composite bundle | Use a stylized clay or clay-animation appearance. |
| 84 | `/3drender` | render-mode | direct + interpretive | Use a high-quality three-dimensional rendered appearance. |
| 85 | `/isometric` | camera-projection | direct | Use an isometric three-dimensional viewpoint. |
| 86 | `/miniature` | scale-style | composite bundle | Make the world read as a tiny model or diorama. |
| 87 | `/tiltshift` | camera-effect | composite bundle | Use selective-focus tilt-shift treatment that can suggest miniature scale. |
| 88 | `/papercraft` | art-medium | composite bundle | Use a layered handmade paper-cut or paper-model treatment. |
| 89 | `/glassart` | material | composite bundle | Use transparent artistic glass as the dominant surface language. |
| 90 | `/chrome` | material | direct | Use a highly reflective chrome-metal surface. |
| 91 | `/holographic` | material-effect | composite bundle | Use emissive, iridescent holographic material behavior. |
| 92 | `/doubleexposure` | composition-effect | direct | Blend two image layers into one visible composition. |
| 93 | `/silhouette` | composition-lighting | composite bundle | Render the subject mainly as a dark outline against brighter light. |
| 94 | `/reflection` | composition-material | composite bundle | Include a reflective surface or mirrored scene reflection. |
| 95 | `/mirror` | composition-material | composite bundle | Build the composition around a literal or conceptual mirror. |
| 96 | `/fire` | effect | direct | Add visible fire and flame as a scene element. |
| 97 | `/smoke` | effect-atmosphere | direct | Add atmospheric smoke that partially obscures the scene. |
| 98 | `/glitch` | effect | composite bundle | Apply digital glitch and distortion treatment. |
| 99 | `/dreamcore` | surreal-style | interpretive | Use a surreal, dreamlike, subtly uncanny visual language. |

## Mapping labels

- **Direct**: relatively concrete camera, atmosphere, material, or effect state.
- **Composite bundle**: expands into several related state contributions.
- **Interpretive**: cultural, stylistic, or quality direction whose artifact meaning remains contextual.
- **Output hint**: requested delivery/detail tier, not proof of native resolution or useful detail.

## Machine-readable companions

- `visual_prompt_aliases.json` is the provenance-bearing manifest for nine numbered alias-group files.
- `visual_state_schema.json` defines 39 valid state paths and value types.
- `visual_blend_rules.json` makes merging deterministic and independent of command order.
- `visual_conflicts.json` exposes contradictory or tense combinations instead of silently overwriting them.
- `visual_compiler_rules.json` defines request shape, compilation stages, and truth boundaries.

## Cross-media boundary

The same state direction can inform an image, animation, or 3D scene. It does not uniquely determine any of them. A visible appearance does not reveal one guaranteed hidden mesh, and a static frame does not reveal one guaranteed animation. Geometry, topology, timing, rigging, simulation, renderer execution, and artifact inspection remain explicit missing state until supplied or built.
