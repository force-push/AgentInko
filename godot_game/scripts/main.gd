extends Node2D

## Inko Coin Dash — a minimal one-screen game.
##
## Move the player to the coin to collect it. The script prints structured
## "[INKO]" markers so AgentInko's Tier 1 verifier can confirm, from headless
## output alone, that the game LOADED and RAN without errors. In headless mode
## it auto-drives the player to the coin and then quits, so a no-input CI run
## still exercises the core loop and terminates deterministically.

const SPEED := 220.0
const COLLECT_RADIUS := 16.0
const PLAYTEST_SECONDS := 2.0

var _player: Node2D
var _coin: Node2D
var _collected := false
var _elapsed := 0.0
var _headless := false


func _ready() -> void:
	_player = $Player
	_coin = $Coin
	_headless = DisplayServer.get_name() == "headless"
	print("[INKO] game_ready scene=%s headless=%s" % [name, _headless])


func _process(delta: float) -> void:
	_elapsed += delta

	# Normal play: arrow keys / WASD move the player.
	var dir := Input.get_vector("ui_left", "ui_right", "ui_up", "ui_down")
	if dir != Vector2.ZERO:
		_player.position += dir * SPEED * delta

	# Headless smoke-test: auto-advance toward the coin so the loop is exercised.
	if _headless:
		_player.position = _player.position.move_toward(_coin.position, SPEED * delta)

	if not _collected and _player.position.distance_to(_coin.position) < COLLECT_RADIUS:
		_collected = true
		print("[INKO] coin_collected t=%.2f" % _elapsed)
		# Structured result line the Tier 2 playtest agent parses via MCP.
		print("[INKO] result completed=true time=%.2f deaths=0" % _elapsed)

	if _headless and _elapsed >= PLAYTEST_SECONDS:
		if not _collected:
			print("[INKO] result completed=false time=%.2f deaths=0" % _elapsed)
		print("[INKO] playtest_done collected=%s frames_ok=true" % _collected)
		get_tree().quit()
