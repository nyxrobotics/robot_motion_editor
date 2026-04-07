# Robot Motion Editor

Robot Motion Editor is a ROS-based system for authoring and executing joint-space animations for humanoid robots.

The system consists of:

* GUI: Python + PyQt (animation editor)
* Backend: C++ + ROS (runtime execution)
* Data format: YAML (persistent storage of animations)

---

## 1. Directory Structure

A workspace is a directory containing YAML files.

```text
workspace/
  ├── animation_1.yaml
  ├── animation_2.yaml
  └── ...
```

Each YAML file defines one animation.

---

## 2. Data Structures

### 2.1 AnimationData

Represents one animation.

Fields:

* `name`: string
* `frames`: list of `FrameData`
* optional branching nodes (`IfData`, `SwitchData`)

---

### 2.2 FrameData

Represents one step in the animation.

Fields:

* `joints`: map<string, double>

  * key: joint name
  * value: target position (radians)

* `move_duration`: double (seconds)

  * duration of interpolation

* `wait_duration`: double (seconds)

  * hold duration after interpolation

* `speed_scale`: map<string, double> (optional)

  * per-joint scaling

---

### 2.3 IfData

Conditional branch node.

Fields (typical):

* condition input (implementation-dependent)
* `true_block`: string
* `false_block`: string

---

### 2.4 SwitchData

Multi-branch node.

Fields (typical):

* input value
* map<value, next_block_name>

---

## 3. YAML Format Example

```yaml
name: wave
frames:
  - joints:
      r_shoulder_pitch: 0.4
      r_elbow_roll: -1.1
    move_duration: 0.6
    wait_duration: 0.1

  - joints:
      r_shoulder_pitch: 0.5
      r_elbow_roll: -0.9
    move_duration: 0.3
    wait_duration: 0.05
```

---

## 4. GUI Implementation (Python / PyQt)

### 4.1 Responsibilities

* Load YAML files using `yaml` (PyYAML)
* Store data in Python objects (dict / list)
* Bind UI widgets to data
* Update data on user interaction
* Serialize data back to YAML

---

### 4.2 Load Flow

```python
for file in workspace_dir:
    data = yaml.safe_load(file)
    animations.append(data)
```

---

### 4.3 Save Flow

```python
for animation in animations:
    yaml.safe_dump(animation, file)
```

---

### 4.4 Important Notes

* Field names must match backend (`joints`, not `joints_data`)
* Missing fields are not auto-filled
* GUI directly edits YAML-equivalent structures

---

## 5. Backend Implementation (C++ / ROS)

Main class: `ActionModule`

---

### 5.1 Core Responsibilities

* Load workspace
* Execute animation
* Interpolate joint values
* Publish commands to robot

---

## 6. Workspace Loading

Function: `loadWorkspace`

Steps:

```cpp
for each file in directory:
    parse YAML
    create AnimationData
    store in map<string, AnimationData>
```

Requirements:

* unique animation names
* valid frame list

---

## 7. Execution Flow

### 7.1 Start Request

Function: `startActionCallback`

```cpp
start_playing_requested_ = true;
current_animation_name_ = request.name;
```

---

### 7.2 Main Loop

Function: `processAnimationStep`

Executed periodically.

Steps:

1. Check start/stop flags
2. Initialize animation if needed
3. Get current frame
4. Update elapsed time
5. Compute joint targets
6. Check move/wait completion
7. Advance frame or branch

---

## 8. Frame Execution

Function: `executeFrame`

### 8.1 Interpolation

For each joint:

```cpp
double duration = move_duration / speed_scale;
double alpha = clamp(elapsed / duration, 0.0, 1.0);
cmd = start + alpha * (goal - start);
```

Where:

* `start`: latched at frame entry
* `goal`: from `frame.joints`

---

### 8.2 Timing

```cpp
if (elapsed < move_duration):
    // interpolate
else if (elapsed < move_duration + wait_duration):
    // hold
else:
    // next frame
```

---

### 8.3 Important Requirements

* Start pose must be stored once per frame
* `elapsed` must be monotonic
* `speed_scale` must be > 0

---

## 9. Joint Command Generation

Function: `createJointTrajectory`

Responsibilities:

* Create ROS trajectory message
* Fill joint names
* Fill positions
* Set timing

Typical message type:

* `trajectory_msgs/JointTrajectory`

---

## 10. State Variables

Used in `ActionModule`:

* `start_playing_requested_`
* `stop_playing_requested_`
* `current_animation_name_`
* `current_frame_index_`
* `elapsed_time_`

---

## 11. State Transitions

```text
IDLE
  -> start request
INIT
  -> frame start
MOVE
  -> move_duration elapsed
WAIT
  -> wait_duration elapsed
NEXT FRAME
  -> repeat or finish
```

---

## 12. Common Implementation Errors

### 12.1 No movement

* interpolation not applied
* goal not written to command

### 12.2 Instant jump

* alpha always 1.0
* start not latched

### 12.3 Stuck in frame

* elapsed not updated
* condition wrong

### 12.4 Playback not starting

* start flag ignored
* animation not found

---

## 13. ROS Integration

### Inputs

* action request (topic or service)

### Outputs

* joint trajectory (`trajectory_msgs/JointTrajectory`)

---

## 14. Required Dependencies

### Python

* PyQt5 or PySide2
* PyYAML

### C++

* ROS (roscpp)
* trajectory_msgs
* std_msgs

---

## 15. Summary

* YAML defines animation data
* GUI edits YAML
* backend loads YAML
* runtime interpolates joint positions
* commands are published to ROS controllers
