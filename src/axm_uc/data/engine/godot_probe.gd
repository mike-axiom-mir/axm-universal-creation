extends SceneTree
## Fixed isolated runtime probe. Input is an embedded GLB plus bounded JSON.

var request: Dictionary
var document := GLTFDocument.new()
var state := GLTFState.new()
var model: Node
var meshes: Array[MeshInstance3D] = []
var players: Array[AnimationPlayer] = []
var environment := Environment.new()
var camera := Camera3D.new()
var report: Dictionary

func _initialize() -> void:
	_run.call_deferred()

func _fail(message: String) -> void:
	var file := FileAccess.open("res://worker-result.json", FileAccess.WRITE)
	file.store_string(JSON.stringify({"error": message}))
	push_error(message)
	quit(2)

func _collect(node: Node) -> void:
	if node is MeshInstance3D:
		meshes.append(node)
	if node is AnimationPlayer:
		players.append(node)
		node.callback_mode_process = AnimationMixer.ANIMATION_CALLBACK_MODE_PROCESS_MANUAL
	for child in node.get_children():
		_collect(child)

func _new_model() -> void:
	if is_instance_valid(model):
		model.free()
	meshes.clear()
	players.clear()
	model = document.generate_scene(state, 30, false, false)
	root.add_child(model)
	_collect(model)
	await _settle()

func _settle() -> void:
	await process_frame
	await RenderingServer.frame_post_draw

func _play(clip: Variant) -> bool:
	if clip == null:
		return true
	var found := false
	for player in players:
		if player.has_animation(str(clip)):
			player.get_animation(str(clip)).loop_mode = Animation.LOOP_NONE
			player.play(str(clip))
			player.advance(0)
			found = true
	return found

func _seek(pose: Dictionary) -> bool:
	await _new_model()
	if not _play(pose.get("clip")):
		return false
	if pose.get("clip") != null:
		for player in players:
			if player.has_animation(str(pose.clip)):
				player.seek(float(pose.get("time_s", 0)), true)
	await _settle()
	return true

func _geometry() -> Dictionary:
	var minimum := Vector3(INF, INF, INF)
	var maximum := Vector3(-INF, -INF, -INF)
	var triangles := 0
	for node in meshes:
		var mesh: Mesh = node.mesh
		if node.skin != null:
			mesh = node.bake_mesh_from_current_skeleton_pose()
		for surface in range(mesh.get_surface_count()):
			var arrays := mesh.surface_get_arrays(surface)
			var points: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
			var indices: PackedInt32Array = arrays[Mesh.ARRAY_INDEX]
			triangles += (indices.size() if not indices.is_empty() else points.size()) / 3
			for vertex in points:
				var world := node.global_transform * vertex
				minimum = minimum.min(world)
				maximum = maximum.max(world)
	return {"bounds_m": {"min": [minimum.x, minimum.y, minimum.z], "max": [maximum.x, maximum.y, maximum.z]}, "triangles": triangles}

func _bindings() -> Array:
	var rows: Array = []
	var roles := {"albedo": BaseMaterial3D.TEXTURE_ALBEDO, "normal": BaseMaterial3D.TEXTURE_NORMAL,
		"roughness": BaseMaterial3D.TEXTURE_ROUGHNESS, "metallic": BaseMaterial3D.TEXTURE_METALLIC,
		"ao": BaseMaterial3D.TEXTURE_AMBIENT_OCCLUSION, "emission": BaseMaterial3D.TEXTURE_EMISSION}
	for node in meshes:
		for surface in range(node.mesh.get_surface_count()):
			var material := node.get_active_material(surface)
			var row := {}
			for role in roles:
				row[role] = false
				if material is BaseMaterial3D:
					var texture: Texture2D = material.get_texture(roles[role])
					if texture != null:
						var decoded := texture.get_image()
						row[role] = decoded != null and not decoded.is_empty() and decoded.get_width() > 0
			rows.append(row)
	return rows

func _frame_camera(view: Dictionary, geometry: Dictionary) -> void:
	var b: Dictionary = geometry.bounds_m
	var low := Vector3(b.min[0], b.min[1], b.min[2])
	var high := Vector3(b.max[0], b.max[1], b.max[2])
	var center := (low + high) * 0.5
	var radius := maxf((high - low).length() * 0.5, 0.01)
	var yaw: float = view.yaw
	var elevation: float = view.elevation
	var direction := Vector3(sin(yaw) * cos(elevation), sin(elevation), cos(yaw) * cos(elevation))
	camera.projection = Camera3D.PROJECTION_ORTHOGONAL
	camera.size = radius * 2.5 * maxf(1.0, float(request.height) / float(request.width))
	camera.near = radius * 0.001
	camera.far = radius * 20.0
	camera.position = center + direction * radius * 4.0
	camera.look_at(center)

func _save_image(name: String) -> void:
	await _settle()
	var image := root.get_texture().get_image()
	image.convert(Image.FORMAT_RGB8)
	if image.save_png("res://" + name + ".png") != OK:
		_fail("Cannot save rendered image " + name)

func _capture(name: String) -> void:
	await _save_image(name)
	var white := StandardMaterial3D.new()
	white.shading_mode = BaseMaterial3D.SHADING_MODE_UNSHADED
	white.albedo_color = Color.WHITE
	for node in meshes:
		node.material_override = white
	environment.background_color = Color.BLACK
	await _save_image(name + "-coverage")
	for node in meshes:
		node.material_override = null
	environment.background_color = Color(0.045, 0.06, 0.085)

func _run() -> void:
	request = JSON.parse_string(FileAccess.get_file_as_string("res://request.json"))
	if DisplayServer.get_name() == "headless":
		_fail("Headless dummy renderer cannot supply rendered evidence")
		return
	root.size = Vector2i(int(request.width), int(request.height))
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	root.add_child(camera)
	camera.current = true
	var world := WorldEnvironment.new()
	environment.background_mode = Environment.BG_COLOR
	environment.background_color = Color(0.045, 0.06, 0.085)
	environment.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	environment.ambient_light_color = Color(0.7, 0.8, 1.0)
	environment.ambient_light_energy = 0.65
	world.environment = environment
	root.add_child(world)
	for rotation in [Vector3(-45, -25, 0), Vector3(-20, 145, 0)]:
		var light := DirectionalLight3D.new()
		light.rotation_degrees = rotation
		light.light_energy = 1.2
		root.add_child(light)
	if document.append_from_file("res://asset.glb", state) != OK:
		_fail("Godot GLTFDocument import failed")
		return
	report = {"backend": {"version": Engine.get_version_info().string,
		"renderer": RenderingServer.get_current_rendering_method(), "display": DisplayServer.get_name(),
		"adapter": RenderingServer.get_video_adapter_name(), "vendor": RenderingServer.get_video_adapter_vendor()},
		"source_sha256": FileAccess.get_sha256("res://asset.glb"), "poses": [], "playback": []}
	for pose in request.poses:
		if not await _seek(pose):
			_fail("Authored clip was not imported under its original name")
			return
		report.poses.append(_geometry())
		if not report.has("material_bindings"):
			report.material_bindings = _bindings()
	for index in range(request.views.size()):
		var view: Dictionary = request.views[index]
		if not await _seek(view):
			_fail("View names an unavailable animation")
			return
		_frame_camera(view, _geometry())
		await _capture("view-%02d" % index)
	if request.playback != null:
		var playback: Dictionary = request.playback
		await _new_model()
		if not _play(playback.clip):
			_fail("Playback clip unavailable")
			return
		await _settle()
		_frame_camera(request.views[0], _geometry())
		for index in range(int(playback.frames)):
			if index > 0:
				for player in players:
					player.advance(1.0 / float(playback.fps))
				await _settle()
			report.playback.append(_geometry())
			await _capture("frame-%03d" % index)
	var file := FileAccess.open("res://worker-result.json", FileAccess.WRITE)
	file.store_string(JSON.stringify(report, "\t", true, true))
	file.close()
	quit(0)
