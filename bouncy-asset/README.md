# Bouncy Component

Makes the player bounce into the air when they land on something. There are two ways to use it:

| | Bouncy Pad | Bouncy component |
|---|---|---|
| File | `bouncy_pad.tscn` | `bouncy.tscn` |
| What it is | A ready-made trampoline you drag into a level | Attach it to **any object** to make that object bouncy |
| Good for | Beginners | Anyone who wants platforms, enemies, rocks… to bounce |

Demo level: open `bouncy_demo.tscn` and press **F6** (Run Current Scene).

---

## Option 1: Place a trampoline

1. Open a level (for example `main.tscn`) and switch to the **2D** view at the top.
2. In the **FileSystem** dock (bottom left), find `components/bouncy/bouncy_pad.tscn` and **drag it into the level**.
3. The trampoline's origin is at the **bottom-centre** of the picture, so place it on the ground.
4. Adjust the settings in the **Inspector** on the right, then press F5 to play.

## Option 2: Make any object bouncy

1. In the **Scene** dock (top left), **right-click** the object you want to make bouncy (for example a Platform) → **Instantiate Child Scene**, and choose `components/bouncy/bouncy.tscn`.
2. Move the new Bouncy node to the object's **top surface** (the pink box should stick out slightly above the surface).
3. Select the CollisionShape2D under Bouncy and drag the handles on the sides of the box so it's as wide as the object.
4. Adjust the settings and press F5 to play.

---

## Settings you can change

| Setting | What it does | Default |
|---|---|---|
| **Bounce Height** | How high the player is launched, in pixels. A normal jump is about 395 | 600 |
| **Hold Jump Boost** | Extra height (%) if the player holds the jump key while landing | 30% |
| **Squash Effect** | Squash-and-stretch effect when bounced on | On |
| **Bounce Sound** | Sound played when bounced on (the pad uses "boing" by default) | — |
| **Texture** (Bouncy Pad only) | The trampoline's picture | Pink trampoline |

> Try this: set Bounce Height to 395 and the bounce will be exactly as high as a normal jump. Then lower the Gravity on GameLogic and bounce again — the height stays the same, but you float in the air for longer!

## Use your own picture

1. Prepare a PNG (about 128 pixels wide, with a transparent background works best).
2. **Drag** the PNG into the **FileSystem** dock (bottom left) — `components/bouncy/` is a good place for it.
3. Select the trampoline in your level, then **drag** the PNG from the FileSystem dock onto the **Texture** field in the Inspector.
4. The collision area resizes to fit the picture automatically — nothing else to change.

To go back to the original picture: right-click the Texture field → **Clear**.

---

## How does it work? (for the curious)

`bouncy.gd` is an **Area2D** (a detection zone). When a player enters the zone while falling, it sets the player's vertical speed to point upwards:

```gdscript
character.velocity.y = -sqrt(2.0 * gravity * height)
```

This is the physics formula **v = √(2gh)**: the starting speed you need to reach a height of h. That's why you only have to enter a *height* — the script works out the speed from the current gravity.
