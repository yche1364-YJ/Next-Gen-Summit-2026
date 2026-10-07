@tool
class_name BouncyPad
extends StaticBody2D
## A ready-made trampoline. Drag it into a level, adjust how high it bounces,
## and swap in your own PNG to change how it looks.
## [br][br]
## The origin is at the bottom-centre of the picture, so place it on the ground.

const DEFAULT_TEXTURE := preload("res://components/bouncy/bouncy_pad.png")

## The trampoline's picture. Use your own PNG; the collision area resizes to fit.
@export var texture: Texture2D = DEFAULT_TEXTURE:
	set = _set_texture

## How high (in pixels) the player is launched. A normal jump is about 395 px.
@export_range(0, 3000, 10, "or_greater", "suffix:px") var bounce_height: float = 600.0:
	set = _set_bounce_height

## Extra height (in %) when the player holds the jump key while landing.
@export_range(0, 200, 5, "suffix:%") var hold_jump_boost: float = 30.0:
	set = _set_hold_jump_boost

## Whether to play a squash-and-stretch effect when bounced on.
@export var squash_effect: bool = true:
	set = _set_squash_effect

## Optional sound to play when bounced on.
@export var bounce_sound: AudioStream:
	set = _set_bounce_sound

@onready var _sprite: Sprite2D = %Sprite2D
@onready var _collision_shape: CollisionShape2D = %CollisionShape2D
@onready var _bouncy: Bouncy = %Bouncy


func _ready() -> void:
	_update()


func _set_texture(value: Texture2D) -> void:
	texture = value if value else DEFAULT_TEXTURE
	_update()


func _set_bounce_height(value: float) -> void:
	bounce_height = value
	_update()


func _set_hold_jump_boost(value: float) -> void:
	hold_jump_boost = value
	_update()


func _set_squash_effect(value: bool) -> void:
	squash_effect = value
	_update()


func _set_bounce_sound(value: AudioStream) -> void:
	bounce_sound = value
	_update()


func _update() -> void:
	if not is_node_ready():
		return

	var size := texture.get_size()

	# Picture sits on top of the origin, so the pad can be placed on the ground
	# and squashes from its base.
	_sprite.texture = texture
	_sprite.centered = true
	_sprite.offset = Vector2(0, -size.y / 2.0)

	# Solid body = the whole picture.
	var body_shape := RectangleShape2D.new()
	body_shape.size = size
	_collision_shape.shape = body_shape
	_collision_shape.position = Vector2(0, -size.y / 2.0)

	# Bouncy area = a strip along the top edge of the picture.
	_bouncy.position = Vector2(0, -size.y)
	var area_shape := RectangleShape2D.new()
	area_shape.size = Vector2(size.x, 48)
	var area_collision: CollisionShape2D = _bouncy.get_node("CollisionShape2D")
	area_collision.shape = area_shape
	area_collision.position = Vector2(0, -16)

	_bouncy.bounce_height = bounce_height
	_bouncy.hold_jump_boost = hold_jump_boost
	_bouncy.squash_effect = squash_effect
	_bouncy.squash_node = _sprite
	_bouncy.bounce_sound = bounce_sound
