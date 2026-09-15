"""Reusable professional game-system visual foundations.

These are auxiliary product surfaces shared by many genres. They extend the same
visual-template v1 catalog and remain optional: shipping a server browser,
matchmaking, chat, privacy or any other surface is a product decision, not an
automatic requirement imposed by the catalog.
"""
from __future__ import annotations

from copy import deepcopy
from typing import Any


def _merge_unique(target: dict[str, Any], additions: dict[str, Any], label: str) -> None:
    overlap=sorted(set(target)&set(additions))
    if overlap:
        raise RuntimeError(f"game-system {label} extension collides: {', '.join(overlap)}")
    target.update(deepcopy(additions))


def _settings_layout() -> dict[str, dict[str, tuple[float,float,float,float]]]:
    return {
        "compact":{"header":(.04,.03,.92,.08),"categories":(.04,.14,.92,.13),"settings":(.04,.30,.92,.54),"actions":(.04,.87,.92,.09)},
        "standard":{"header":(.03,.03,.94,.08),"categories":(.03,.14,.20,.82),"settings":(.26,.14,.71,.68),"actions":(.26,.85,.71,.11)},
        "wide":{"header":(.025,.03,.95,.075),"categories":(.025,.14,.18,.82),"settings":(.23,.14,.745,.68),"actions":(.23,.85,.745,.11)},
    }


def _browser_layout() -> dict[str, dict[str, tuple[float,float,float,float]]]:
    return {
        "compact":{"header":(.03,.03,.94,.08),"filters":(.03,.14,.94,.10),"list":(.03,.27,.58,.60),"details":(.64,.27,.33,.43),"actions":(.64,.73,.33,.14)},
        "standard":{"header":(.025,.03,.95,.08),"filters":(.025,.14,.18,.82),"list":(.23,.14,.47,.82),"details":(.73,.14,.245,.58),"actions":(.73,.75,.245,.21)},
        "wide":{"header":(.02,.03,.96,.075),"filters":(.02,.14,.16,.82),"list":(.205,.14,.52,.82),"details":(.75,.14,.23,.58),"actions":(.75,.75,.23,.21)},
    }


def _gallery_layout() -> dict[str, dict[str, tuple[float,float,float,float]]]:
    return {
        "compact":{"header":(.03,.03,.94,.08),"categories":(.03,.14,.94,.10),"gallery":(.03,.27,.94,.48),"details":(.03,.78,.60,.18),"actions":(.66,.78,.31,.18)},
        "standard":{"header":(.025,.03,.95,.08),"categories":(.025,.14,.18,.82),"gallery":(.23,.14,.50,.82),"details":(.755,.14,.22,.58),"actions":(.755,.75,.22,.21)},
        "wide":{"header":(.02,.03,.96,.075),"categories":(.02,.14,.15,.82),"gallery":(.195,.14,.55,.82),"details":(.77,.14,.21,.58),"actions":(.77,.75,.21,.21)},
    }


def extend_game_system_catalog(namespace: dict[str,Any]) -> None:
    styles=namespace["STYLE_SYSTEMS"]
    primitives=namespace["PRIMITIVES"]
    screens=namespace["SCREEN_TEMPLATES"]
    products=namespace["PRODUCT_ARCHETYPES"]
    screen=namespace["_screen"]
    origin=namespace["_origin"]
    product_schema=namespace["PRODUCT_SCHEMA"]

    _merge_unique(styles,{
        "game.system.neutral":{
            "intent":"genre-neutral game product surfaces with explicit state, ownership, consequences and recovery",
            "tokens":{"canvas":"#0a0f15","surface":"#121b24","surface_raised":"#1b2733","text":"#eff5f6","muted":"#9eacb3","accent":"#83c9ff","warning":"#f0c36e","danger":"#ee7777","line":"#34444f"},
            "shape":{"panel_radius_ratio":.014,"cut_ratio":.003,"line_ratio":.0013},
            "type":{"display_weight":730,"body_weight":500,"metric_scale":1.55,"tracking":.014},
            "depth":{"layers":4,"shadow":"subtle","glass":"restrained"},
            "motion":{"fast_ms":90,"standard_ms":175,"slow_ms":300,"principle":"state and ownership before flourish"},
        }
    },"style")

    _merge_unique(primitives,{
        "keybind-row":{"role":"map one player action to explicit device input","states":["bound","unbound","focused","listening","conflict","disabled"],"conflicts_must_be_explicit":True},
        "save-slot":{"role":"represent one recoverable persisted state","states":["empty","occupied","autosave","read-only","incompatible","corrupt"],"destructive_overwrite_requires_confirmation":True},
        "party-member":{"role":"show participant identity, seat, readiness and communication state","states":["local","remote","ai","joining","ready","disconnected"],"seat_identity_must_be_explicit":True},
        "server-row":{"role":"compare joinable session state","states":["available","full","locked","incompatible","unreachable"],"availability_must_be_observed":True},
        "notification-badge":{"role":"surface changed state without replacing its source","states":["none","unread","warning","critical"],"count_must_not_be_fabricated":True},
        "chat-message":{"role":"show authored communication with source identity and time ordering","states":["normal","system","failed","pending"],"author_source_must_be_visible":True},
        "confirmation-summary":{"role":"summarize consequence before consequential commitment","states":["review","confirm","cancel","busy"],"must_show_scope_and_consequence":True},
        "focus-indicator":{"role":"show current navigational focus across input methods","states":["keyboard","gamepad","touch","pointer","hidden"],"focus_cannot_rely_on_color_alone":True},
    },"primitive")

    quality=[
        "current state and scope must be visible before consequential actions",
        "focus, selection and ownership must not depend on color alone",
        "network or persistence success may only be shown when observed",
        "reversible actions expose cancel/back paths and destructive actions expose consequences",
        "templates must remain useful with controller/keyboard navigation even when pointer input exists",
    ]

    new_screens={
        "game.system.profile":screen(
            "game.system.profile","Player profile","game.system","game.system.neutral",
            "show identity, progression, recent activity and editable presentation without mixing account ownership with game performance",
            {
                "compact":{"identity":(.04,.04,.92,.20),"progress":(.04,.27,.92,.15),"stats":(.04,.45,.45,.33),"recent":(.52,.45,.44,.33),"actions":(.04,.82,.92,.13)},
                "standard":{"identity":(.04,.05,.27,.78),"progress":(.34,.05,.62,.16),"stats":(.34,.25,.29,.46),"recent":(.66,.25,.30,.46),"actions":(.34,.76,.62,.12)},
                "wide":{"identity":(.035,.05,.24,.79),"progress":(.31,.05,.66,.15),"stats":(.31,.24,.31,.47),"recent":(.65,.24,.32,.47),"actions":(.31,.77,.66,.11)},
            },tags=["game","system","profile","identity"],quality=quality),
        "game.system.party":screen(
            "game.system.party","Party and seat management","game.system","game.system.neutral",
            "manage human and machine participants with explicit seat ownership, readiness and invitation state",
            {
                "compact":{"header":(.03,.03,.94,.08),"members":(.03,.14,.94,.47),"invite":(.03,.64,.46,.25),"rules":(.52,.64,.45,.25),"actions":(.03,.92,.94,.05)},
                "standard":{"header":(.025,.03,.95,.08),"members":(.025,.14,.52,.74),"invite":(.565,.14,.41,.32),"rules":(.565,.49,.41,.24),"actions":(.565,.77,.41,.11)},
                "wide":{"header":(.02,.03,.96,.075),"members":(.02,.14,.56,.75),"invite":(.61,.14,.37,.32),"rules":(.61,.49,.37,.25),"actions":(.61,.78,.37,.11)},
            },tags=["game","system","party","seats"],quality=quality),
        "game.system.matchmaking":screen(
            "game.system.matchmaking","Matchmaking queue","game.system","game.system.neutral",
            "show selected activity, party eligibility, observed queue state and a reliable cancel path",
            {
                "compact":{"activity":(.05,.07,.90,.22),"party":(.05,.33,.90,.20),"queue":(.05,.57,.90,.20),"actions":(.05,.81,.90,.12)},
                "standard":{"activity":(.08,.12,.34,.60),"party":(.46,.12,.22,.60),"queue":(.72,.12,.20,.36),"actions":(.72,.53,.20,.19)},
                "wide":{"activity":(.10,.12,.34,.62),"party":(.47,.12,.22,.62),"queue":(.72,.12,.18,.37),"actions":(.72,.54,.18,.20)},
            },tags=["game","system","matchmaking","network"],quality=quality+["queue time estimates must be labeled estimates, not promises"]),
        "game.system.server-browser":screen(
            "game.system.server-browser","Server / session browser","game.system","game.system.neutral",
            "compare observed joinable sessions with filters, compatibility state and explicit connection choice",
            _browser_layout(),tags=["game","system","server","network"],quality=quality),
        "game.system.controller-remap":screen(
            "game.system.controller-remap","Controller and input remapping","game.system","game.system.neutral",
            "map actions to current input devices while exposing conflicts, defaults and seat/device ownership",
            {
                "compact":{"header":(.03,.03,.94,.08),"device":(.03,.14,.94,.12),"bindings":(.03,.29,.58,.57),"conflicts":(.64,.29,.33,.30),"actions":(.64,.63,.33,.23)},
                "standard":{"header":(.025,.03,.95,.08),"device":(.025,.14,.20,.82),"bindings":(.25,.14,.47,.82),"conflicts":(.745,.14,.23,.42),"actions":(.745,.60,.23,.36)},
                "wide":{"header":(.02,.03,.96,.075),"device":(.02,.14,.18,.82),"bindings":(.225,.14,.50,.82),"conflicts":(.75,.14,.23,.42),"actions":(.75,.60,.23,.36)},
            },tags=["game","system","controls","remap"],quality=quality+["binding conflicts must be shown before replacement"]),
        "game.system.display":screen(
            "game.system.display","Display and graphics settings","game.system","game.system.neutral",
            "show display/graphics settings with current values, performance consequence and a safe confirmation path",
            {
                "compact":{"preview":(.04,.03,.92,.26),"categories":(.04,.32,.92,.10),"settings":(.04,.45,.60,.40),"impact":(.67,.45,.29,.25),"actions":(.67,.73,.29,.12)},
                "standard":{"preview":(.03,.03,.34,.78),"categories":(.40,.03,.18,.78),"settings":(.61,.03,.36,.58),"impact":(.61,.64,.17,.17),"actions":(.81,.64,.16,.17)},
                "wide":{"preview":(.025,.03,.40,.80),"categories":(.45,.03,.16,.80),"settings":(.635,.03,.34,.59),"impact":(.635,.66,.16,.17),"actions":(.815,.66,.16,.17)},
            },tags=["game","system","display","graphics"],quality=quality+["display-mode changes need a bounded revert path when confirmation is required"]),
        "game.system.audio":screen(
            "game.system.audio","Audio settings","game.system","game.system.neutral",
            "make master, dialogue, music, effects, voice and dynamic-range choices independently readable",
            _settings_layout(),tags=["game","system","audio","settings"],quality=quality),
        "game.system.accessibility":screen(
            "game.system.accessibility","Shared game accessibility","game.system","game.system.neutral",
            "group visual, audio, input, cognitive and assistance options with previews that state their limits",
            {
                "compact":{"header":(.04,.03,.92,.08),"categories":(.04,.14,.92,.12),"options":(.04,.29,.58,.55),"preview":(.65,.29,.31,.38),"actions":(.65,.71,.31,.13)},
                "standard":{"header":(.03,.03,.94,.08),"categories":(.03,.14,.20,.82),"options":(.26,.14,.43,.70),"preview":(.72,.14,.25,.48),"actions":(.72,.66,.25,.18)},
                "wide":{"header":(.025,.03,.95,.075),"categories":(.025,.14,.18,.82),"options":(.23,.14,.46,.70),"preview":(.72,.14,.255,.48),"actions":(.72,.66,.255,.18)},
            },tags=["game","system","accessibility","settings"],quality=quality+["accessibility labels use plain consequences rather than unexplained expert terminology"]),
        "game.system.save-slots":screen(
            "game.system.save-slots","Save / load slots","game.system","game.system.neutral",
            "show exact save identity, timestamp/progress metadata, compatibility and overwrite/delete consequences",
            _browser_layout(),tags=["game","system","save","load"],quality=quality+["corrupt or incompatible saves remain visible as such; never silently rewrite them"]),
        "game.system.achievements":screen(
            "game.system.achievements","Achievements and challenges","game.system","game.system.neutral",
            "browse completed and incomplete goals without disguising hidden or unobserved progress",
            _gallery_layout(),tags=["game","system","achievements","progress"],quality=quality),
        "game.system.tutorial":screen(
            "game.system.tutorial","Tutorial / training lesson","game.system","game.system.neutral",
            "teach one bounded mechanic with visible goal, demonstration space, input hint and repeat/skip choice",
            {
                "compact":{"goal":(.04,.04,.92,.13),"demo":(.04,.20,.92,.42),"steps":(.04,.65,.56,.25),"input":(.63,.65,.33,.12),"actions":(.63,.80,.33,.10)},
                "standard":{"lessons":(.025,.03,.18,.94),"demo":(.23,.03,.51,.70),"goal":(.765,.03,.21,.22),"steps":(.765,.28,.21,.32),"input":(.23,.77,.51,.09),"actions":(.765,.64,.21,.22)},
                "wide":{"lessons":(.02,.03,.16,.94),"demo":(.205,.03,.56,.71),"goal":(.79,.03,.19,.22),"steps":(.79,.28,.19,.33),"input":(.205,.78,.56,.09),"actions":(.79,.65,.19,.22)},
            },tags=["game","system","tutorial","training"],quality=quality+["skip/repeat consequences must be explicit when tutorial state affects progress"]),
        "game.system.photo-mode":screen(
            "game.system.photo-mode","Photo mode","game.system","game.system.neutral",
            "keep the captured world dominant while camera, lens, effects and output controls remain inspectable",
            {
                "compact":{"world":(0,0,1,1),"camera":(.03,.04,.28,.36),"effects":(.69,.04,.28,.36),"capture":(.35,.82,.30,.14)},
                "standard":{"world":(0,0,1,1),"camera":(.025,.04,.20,.52),"effects":(.775,.04,.20,.52),"capture":(.36,.84,.28,.11)},
                "wide":{"world":(0,0,1,1),"camera":(.02,.04,.17,.52),"effects":(.81,.04,.17,.52),"capture":(.39,.85,.22,.10)},
            },tags=["game","system","photo","camera"],quality=quality),
        "game.system.credits":screen(
            "game.system.credits","Credits and licenses","game.system","game.system.neutral",
            "present people, contributors, licenses and acknowledgements accessibly without hiding provenance behind animation",
            {
                "compact":{"header":(.05,.04,.90,.10),"credits":(.05,.18,.90,.58),"navigation":(.05,.80,.42,.14),"actions":(.53,.80,.42,.14)},
                "standard":{"navigation":(.04,.05,.20,.84),"credits":(.28,.05,.48,.84),"licenses":(.80,.05,.16,.62),"actions":(.80,.71,.16,.18)},
                "wide":{"navigation":(.04,.05,.17,.84),"credits":(.25,.05,.52,.84),"licenses":(.80,.05,.16,.62),"actions":(.80,.71,.16,.18)},
            },tags=["game","system","credits","provenance"],quality=quality),
        "game.system.error-recovery":screen(
            "game.system.error-recovery","Error and recovery","game.system","game.system.neutral",
            "state what failed, what remains safe, what can be retried and which diagnostic evidence is available",
            {
                "compact":{"context":(0,0,1,1),"error":(.12,.13,.76,.20),"safe-state":(.18,.37,.64,.16),"recovery":(.18,.57,.64,.25)},
                "standard":{"context":(0,0,1,1),"error":(.23,.14,.54,.18),"safe-state":(.29,.37,.42,.15),"recovery":(.29,.57,.42,.24)},
                "wide":{"context":(0,0,1,1),"error":(.28,.14,.44,.18),"safe-state":(.33,.37,.34,.15),"recovery":(.33,.57,.34,.24)},
            },tags=["game","system","error","recovery"],quality=quality+["failure text must not imply data loss or recovery success without evidence"]),
        "game.system.notifications":screen(
            "game.system.notifications","Notification center","game.system","game.system.neutral",
            "show sourced changes and alerts with filtering/read-state without turning unread count into an engagement target",
            _browser_layout(),tags=["game","system","notifications","alerts"],quality=quality),
        "game.system.chat":screen(
            "game.system.chat","Text chat and channels","game.system","game.system.neutral",
            "show channel, author and delivery state while keeping mute/block/report controls reachable",
            {
                "compact":{"channels":(.03,.03,.94,.10),"messages":(.03,.16,.65,.65),"members":(.71,.16,.26,.45),"composer":(.03,.84,.65,.12),"actions":(.71,.65,.26,.31)},
                "standard":{"channels":(.02,.03,.18,.94),"messages":(.225,.03,.52,.72),"members":(.77,.03,.21,.55),"composer":(.225,.79,.52,.18),"actions":(.77,.62,.21,.35)},
                "wide":{"channels":(.018,.03,.16,.94),"messages":(.20,.03,.56,.72),"members":(.785,.03,.197,.55),"composer":(.20,.79,.56,.18),"actions":(.785,.62,.197,.35)},
            },tags=["game","system","chat","communication"],quality=quality+["pending/failed message delivery must not look delivered","author identity must accompany messages"]),
        "game.system.privacy-consent":screen(
            "game.system.privacy-consent","Privacy and consent","game.system","game.system.neutral",
            "show optional data/network scopes, purpose, current choice and revocation path without preselecting consent",
            {
                "compact":{"header":(.04,.03,.92,.09),"scope":(.04,.15,.92,.16),"choices":(.04,.34,.92,.42),"consequence":(.04,.79,.56,.16),"actions":(.63,.79,.33,.16)},
                "standard":{"header":(.04,.04,.92,.10),"scope":(.04,.19,.24,.67),"choices":(.31,.19,.39,.67),"consequence":(.73,.19,.23,.43),"actions":(.73,.66,.23,.20)},
                "wide":{"header":(.05,.04,.90,.10),"scope":(.05,.19,.23,.67),"choices":(.31,.19,.40,.67),"consequence":(.74,.19,.21,.43),"actions":(.74,.66,.21,.20)},
            },tags=["game","system","privacy","consent"],quality=quality+["consent is opt-in unless a different lawful/product contract is explicitly established","revocation path must be as discoverable as acceptance"]),
        "game.system.language":screen(
            "game.system.language","Language and text","game.system","game.system.neutral",
            "choose interface, subtitle and voice language with readable previews and explicit download/availability state where applicable",
            {
                "compact":{"header":(.04,.03,.92,.08),"languages":(.04,.14,.44,.70),"text-preview":(.52,.14,.44,.32),"voice":(.52,.49,.44,.20),"actions":(.52,.73,.44,.11)},
                "standard":{"header":(.03,.03,.94,.08),"languages":(.03,.14,.28,.82),"text-preview":(.34,.14,.39,.55),"voice":(.76,.14,.21,.36),"actions":(.76,.54,.21,.15)},
                "wide":{"header":(.025,.03,.95,.075),"languages":(.025,.14,.26,.82),"text-preview":(.315,.14,.43,.55),"voice":(.78,.14,.195,.36),"actions":(.78,.54,.195,.15)},
            },tags=["game","system","language","localization"],quality=quality+["unavailable language assets must be labeled unavailable rather than silently falling back"]),
    }
    _merge_unique(screens,new_screens,"screen")

    system_screens=list(new_screens)
    flow=[
        ["game.system.profile","game.system.party","open-party"],
        ["game.system.party","game.system.matchmaking","find-match"],
        ["game.system.matchmaking","game.system.server-browser","browse-sessions"],
        ["game.system.controller-remap","game.system.accessibility","accessibility"],
        ["game.system.display","game.system.audio","next-settings"],
        ["game.system.audio","game.system.accessibility","next-settings"],
        ["game.system.save-slots","game.system.error-recovery","recover-failure"],
        ["game.system.notifications","game.system.chat","open-message"],
        ["game.system.privacy-consent","game.system.profile","return-profile"],
        ["game.system.language","game.system.accessibility","return-settings"],
        ["game.system.tutorial","game.system.achievements","view-progress"],
        ["game.system.photo-mode","game.system.notifications","capture-complete"],
        ["game.system.credits","game.system.privacy-consent","privacy"],
    ]
    _merge_unique(products,{
        "game.system.shell":{
            "schema":product_schema,"id":"game.system.shell","version":1,"name":"Professional shared game-system shell","kind":"product","domain":"game.system",
            "tags":["game","system","product","shared"],"origin":origin(),"style":"game.system.neutral",
            "intent":"a reusable library of mature game-product surfaces that genre products can adopt selectively",
            "screens":system_screens,"flow":flow,
            "quality":[
                "system surfaces remain optional capabilities rather than mandatory online/account assumptions",
                "network, persistence and delivery state tell the truth about what is observed",
                "privacy/consent never preselects user agreement merely to improve conversion",
                "input and accessibility surfaces preserve explicit focus and consequence state",
                "errors preserve known-safe state and recovery evidence instead of optimistic success claims",
            ],
        }
    },"product")
