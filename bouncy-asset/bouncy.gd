@tool
class_name Bouncy
extends Area2D
## A bouncy component. Add it as a child of any object (a platform, an enemy,
## a rock...) and players who land on top of it get launched into the air.
## [br][br]
## Rotate the object to change the direction: rotated 90° it becomes a bouncy
## wall that pushes the player sideways. [member launch_angle] tilts the launch
## direction further. In the editor, a yellow arrow shows where it launches.
## [br][br]
## How to use:
## [br]1. In the Scene dock, right-click an object → Instantiate Child Scene →
## choose [code]bouncy.tscn[/code].
## [br]2. Move the Bouncy node to the object's top surface. The pink box should
## stick out slightly above the surface.
## [br]3. Set [member zone_width] so the pink box is as wide as the object.
## [br]4. Adjust [member bounce_height] in the Inspector.

## How high (in pixels) the player is launched. For comparison, a normal jump
## is about 395 pixels.
@export_range(0, 3000, 10, "or_greater", "suffix:px") var bounce_height: float = 600.0

## Tilts the launch direction, in degrees. [code]0[/code] = straight out of the
## bouncy surface. Positive tilts clockwise, negative counterclockwise. The yellow
## arrow in the editor shows the direction. With a tilt, part of the force goes
## sideways, so the player goes less high than [member bounce_height].
@export_range(-180, 180, 1, "suffix:°") var launch_angle: float = 0.0:
	set = _set_launch_angle

## How wide the bounce zone (the pink box) is, in pixels. Make it as wide as the
## object it sits on. A Platform is 128 px per tile, so a Platform with width 2
## needs 256.
@export_range(16, 2048, 1, "or_greater", "suffix:px") var zone_width: float = 128.0:
	set = _set_zone_width

## Extra height (in %) when the player holds the jump key while landing.
@export_range(0, 200, 5, "suffix:%") var hold_jump_boost: float = 30.0

## Whether to play a squash-and-stretch effect when bounced on.
@export var squash_effect: bool = true

## Which node to squash. If empty, the parent node is squashed.
@export var squash_node: Node2D

## Optional sound to play when bounced on.
@export var bounce_sound: AudioStream

## Emitted every time a player is bounced.
signal bounced(body: Node2D)

## After a sideways launch, the player can't steer left/right for this long, so
## the push actually carries them away (the Player script otherwise brakes
## sideways movement almost instantly).
const PUSH_TIME := 0.4

## Length of the direction arrow drawn in the editor.
const ARROW_LENGTH := 110.0

var _sfx: AudioStreamPlayer
var _tween: Tween
var _squash_original_scale := Vector2.ONE


func _set_zone_width(value: float) -> void:
	zone_width = value
	_update_zone()


func _set_launch_angle(value: float) -> void:
	launch_angle = value
	queue_redraw()


## The direction the player is launched in, in world space.
func launch_direction() -> Vector2:
	return Vector2.UP.rotated(global_rotation + deg_to_rad(launch_angle))


## The direction the bouncy surface faces, in world space.
func surface_normal() -> Vector2:
	return Vector2.UP.rotated(global_rotation)


func _update_zone() -> void:
	if not is_node_ready():
		return
	var shape_node := get_node_or_null("CollisionShape2D") as CollisionShape2D
	if not shape_node:
		return
	var rect := shape_node.shape as RectangleShape2D
	if not rect:
		rect = RectangleShape2D.new()
		rect.size = Vector2(zone_width, 48)
		shape_node.shape = rect
	rect.size.x = zone_width
	queue_redraw()


# Editor only: a yellow arrow showing where the player will be launched.
func _draw() -> void:
	if not Engine.is_editor_hint():
		return
	var shape_node := get_node_or_null("CollisionShape2D") as Node2D
	var start := shape_node.position if shape_node else Vector2.ZERO
	var dir := Vector2.UP.rotated(deg_to_rad(launch_angle))
	var tip := start + dir * ARROW_LENGTH
	var side := dir.orthogonal() * 14.0
	var head := PackedVector2Array([tip + dir * 6.0, tip - dir * 22.0 + side, tip - dir * 22.0 - side])
	var outline := Color(0.03, 0.03, 0.1, 0.9)
	var yellow := Color(1.0, 0.84, 0.04)
	draw_line(start, tip - dir * 18.0, outline, 9.0)
	draw_line(start, tip - dir * 18.0, yellow, 5.0)
	draw_colored_polygon(head, yellow)
	draw_polyline(PackedVector2Array([head[0], head[1], head[2], head[0]]), outline, 2.0)
	draw_circle(start, 6.0, yellow)


func _ready() -> void:
	_update_zone()
	if Engine.is_editor_hint():
		return

	# Only detect the player; nothing needs to detect this area.
	collision_layer = 0
	set_collision_mask_value(Global.PhysicsLayers.PLAYER, true)
	monitoring = true

	body_entered.connect(_on_body_entered)


func _get_squash_target() -> Node2D:
	if squash_node:
		return squash_node
	return get_parent() as Node2D


## The upwards speed needed to reach [param height] pixels: v = √(2 × gravity × height).
static func velocity_for_height(height: float, gravity: float) -> float:
	if height <= 0 or gravity <= 0:
		return 0.0
	return sqrt(2.0 * gravity * height)


func _on_body_entered(body: Node2D) -> void:
	if not body.is_in_group("players"):
		return
	if not body is CharacterBody2D:
		return

	var character := body as CharacterBody2D

	# Only bounce when the player comes at the bouncy side of the surface
	# (falling onto it, for one lying flat), not from behind or moving away.
	var normal := surface_normal()
	if character.velocity.dot(normal) > 0.0:
		return
	if (character.global_position - global_position).dot(normal) < 0.0:
		return

	bounce(character)


## Launch [param character] in [method launch_direction]. Other scripts can call this too.
func bounce(character: CharacterBody2D) -> void:
	var gravity: float = ProjectSettings.get_setting("physics/2d/default_gravity")
	if "gravity" in character:
		gravity = character.gravity

	var height := bounce_height
	if "player" in character and Input.is_action_pressed(Actions.lookup(character.player, "jump")):
		height *= 1.0 + hold_jump_boost / 100.0

	var speed := velocity_for_height(height, gravity)
	var dir := launch_direction()
	if absf(dir.x) < 0.001:
		# Straight up (or down): keep the player's sideways movement.
		character.velocity.y = dir.y * speed
	else:
		character.velocity = dir * speed
		if absf(dir.x) > 0.05:
			_hold_sideways_push(character)

	# The Player script stops applying gravity for a moment after it touches
	# the ground ("coyote time"). Reset it so the bounce height is accurate.
	if "coyote_timer" in character:
		character.coyote_timer = 0
	if "jump_buffer_timer" in character:
		character.jump_buffer_timer = 0

	if bounce_sound:
		if not _sfx:
			_sfx = AudioStreamPlayer.new()
			add_child(_sfx)
		_sfx.stream = bounce_sound
		_sfx.play()
	if squash_effect:
		_squash()

	bounced.emit(character)


# Stop the player braking sideways for PUSH_TIME seconds, so a sideways launch
# carries them away. Uses the Player's own "acceleration" setting, so the
# original Player script doesn't need to change.
func _hold_sideways_push(character: CharacterBody2D) -> void:
	if not "acceleration" in character:
		return
	var original: float = character.get_meta("bouncy_original_acceleration", character.acceleration)
	character.set_meta("bouncy_original_acceleration", original)
	character.acceleration = 0.0
	character.get_tree().create_timer(PUSH_TIME).timeout.connect(
		Callable(character, "set").bind("acceleration", original), CONNECT_ONE_SHOT
	)


func _squash() -> void:
	var target := _get_squash_target()
	if not target:
		return

	if _tween and _tween.is_running():
		_tween.kill()
	else:
		_squash_original_scale = target.scale
	var s := _squash_original_scale
	target.scale = s
	_tween = create_tween()
	_tween.tween_property(target, "scale", s * Vector2(1.25, 0.7), 0.06)
	_tween.tween_property(target, "scale", s * Vector2(0.9, 1.15), 0.08)
	_tween.tween_property(target, "scale", s, 0.12)
