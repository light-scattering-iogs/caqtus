# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [6.9.0] - 2024-09-22

### Changed

- Renamed `caqtus.utils.contextlib` to `caqtus.utils.context_managers`
- Clearing a sequence in Condetrol will pop a message box during the operation, with the
  possibility to cancel the operation
- Saving shot data is now asynchronous and does not block shot execution

### Deprecated

- `ShotContext.get_variables` in favor of `ShotContext.get_parameters`

## [6.8.1] - 2024-09-13

### Fixed

- Snapshot crashing when trying to display an image

## [6.8.0] - 2024-09-11

### Added

- A tutorial on how to load and analyze data from a sequence

### Changed

- Polars expressions for quantity and stats now preserve the name of the columns

## [6.7.1] - 2024-09-11

### Fixed

- Bug making it impossible to add a new device configuration
- Background not being subtracted in image view in SnapShot

## [6.7.0] - 2024-09-09

### Added

- Possibility to rename and move sequence paths in Condetrol

### Fixed

- Reduced latency when creating or deleting a sequence path in Condetrol

## [6.6.1] - 2024-09-07

### Fixed

- Bug preventing to run a sequence

### Removed

- Dependency on pydantic

## [6.6.0] - 2024-09-07

### Changed

- Time is now expressed as a decimal number during shot compilation

## [6.5.0] - 2024-09-03

### Changed

- Lines for the steps in the sequence editor are now always overlayed on top of the
  sequence lanes

### Fixed

- Add step button staying enabled when sequence is not editable

## [6.4.0] - 2024-08-31

### Added

- Button to add step in sequence editor

### Fixed

- Display of error message when could not evaluate an expression
- Crash when arange loop has incompatible units

## [6.3.2] - 2024-08-26

### Fixed

- Exceptions while running sequences no longer crash condetrol

## [6.3.3] - 2024-08-26

### Fixed

- Bug causing sequence interruption to be ignored

## [6.3.0] - 2024-08-26

### Added

- `caqtus.session.Sequence` will suggest a path if the specified path does not exist
- Possibility to start a sequence with the *F5* key
- Function `caqtus.experiment.upgrade_database` to initialize and upgrade the database
  schema

### Changed

- User errors are now saved in the sequence and can be displayed at any time in the
  sequence editor

## [6.2.1] - 2024-08-23

### Fixed

- Bug were cancelled exceptions were not correctly handled if an error occurs while
  controlling a device

## [6.2.0] - 2024-08-22

### Changed

- Give better error context when an issue occurs while controlling a device in a shot

### Fixed

- Crash when analog ramp has a duration of zero seconds

## [6.1.0] - 2024-08-21

### Added

- Better error message when a device times out

### Fixed

- Bug causing crash on exception

### [6.0.1] - 2024-08-20

### Fixed

- Bug causing sequence hanging sometimes after an error occurred

## [6.0.0] - 2024-08-20

### Changed

- Sequencers can now interrupt their sequence if an error occurs after the sequence has
  been started.
- Device proxy know use an async converter object to call underlying device methods
  instead of a rpc client.

## [5.5.0] - 2024-08-20

### Added

- Widget to select trigger for a sequencer

### Fixed

- Import for deprecated module `caqtus.utils.roi`

## [5.4.0] - 2024-08-20

### Added

- Function to evaluate parallel sequencer instructions

### Deprecated

- Module `caqtus.utils.roi` in favor of `caqtus.types.image.roi`

## [5.3.0] - 2024-08-18

### Changed

- Many undocumented packages are now private

### Added

- Help menu in Condetrol
- Better error messages when a camera times out
- Better error messages when failing to compute the output of a sequencer

### Documentation

- Added API reference for public classes and functions
- Added condetrol manual

## [5.2.1] - 2024-08-14

### Fixed

- Bug causing sequencer configuration editor to not display correct time step

## [5.2.0] - 2024-08-14

### Added

- Possibility to wait for specific times during a shot while controlling a device

### Fixed

- Bug where it was not possible to set the correct region of interest in the camera
  configuration editor
- Bug causing sequencer configuration editor to not display correct time step

### Changed

- Several non documented packages are now private

## [5.1.0] - 2024-08-11

### Changed

- The time step for a sequencer can now be a decimal value and is no longer required to
  be an integer number of nanoseconds.

## [5.0.2] - 2024-08-10

### Fixed

- Piecewise linear calibration for analog sequencer displays the correct curve when
  using non-linear units

## [5.0.1] - 2024-08-10

### Fixed

- Incompatibility with numpy 1.26
- Bug with camera compiler not signaling used lane

## [5.0.0] - 2024-08-10

### Added

- Documentation for sequencer instructions
- Utility functions to visualize instructions for a sequencer
- Actions to copy/paste from clipboards sequence iterations and time lanes

### Changed

- **Breaking:** Ramps in logarithmic units are now linear in the base space and not in
  the log space.
- **Breaking:** Trigger compilation is now delegated to the compiler of the device to be
  triggered.
- Upgraded to numpy 2.0
- Upgraded to polars 1.3

### Deprecated

- Some methods of timelanes

## [4.16.0] - 2024-07-22

### Changed

- Camera configuration editor is now consistent with other device configuration editors

### Fixed

- Bug which caused device configurations to not always be saved in the device
  configuration dialog

## [4.15.0] - 2024-07-10

### Added

- Possibility to put complex transformations for device output

## [4.13.4] - 2024-07-09

### Fixed

- Crash when expressing sequence loops with incompatible units

## [4.13.0] - 2024-07-06

### Added

- Better event loop for SnapShot application

## [4.12.0] - 2024-07-06

### Added

- Better error handling and logging for experiment server and device server

## [4.11.0] - 2024-07-03

### Added

- Howto documentation for raising recoverable errors
- Documentation for camera device

### Changed

- Simplify camera device interface

## [4.10.3] - 2024-07-03

### Fixed

- Bug which crashed the application if the cell in a lane does not evaluate to the
  correct type

## [4.10.2] - 2024-07-03

### Fixed

- Don't display time lanes context menu when the sequence is not editable

## [4.10.1] - 2024-07-03

### Fixed

- Bug which caused Condetrol to crash when trying to interact with non-editable sequence

## [4.8.0] - 2024-06-30

### Added

- Documentation for recoverable errors

### Fixed

- Infinite recursion error when camera times out too many times

## [4.5.0] - 2024-06-30

### Added

- Highlight of sequence steps in error messages

## [4.4.0] - 2024-06-30

### Added

- Highlight of some caqtus objects in error messages

## [4.3.0] - 2024-06-30

### Added

- Better error message when an error occurs while connecting to a remote server

## [4.2.0] - 2024-06-30

### Added

- Better error messages when an exception occurs on a remote device

### Fixed

- Remote iteration on device server

## [4.1.0] - 2024-06-29

### Added

- Structured logging for device controller

### Fixed

- Used trio instead of asyncio for rpc server

## [4.0.0] - 2024-06-29

### Changed

- Display better error messages when an error occurs while running a sequence
- Replaced grpc remote devices with anyio remote devices

## [3.8.0] - 2024-06-28

### Added

- HOWTO for creating device extension
- Function to get a copy of caqtus serialization converter
- Export `FormDeviceConfigurationEditor`
  in `caqtus.gui.condetrol.device_configuration_editors`

### Changed

- Required methods of `Device` class are now abstract

## [3.7.0] - 2024-06-23

### Changed

- Shots are run in the order they are defined

## [3.6.0] - 2024-06-21

### Added

- Minimize and maximize buttons for device configuration dialog

### Changed

- Load only sequence specific parameters by default

## [3.5.1] - 2024-06-16

### Fixed

- Bug which caused condetrol to crash sometimes when deleting a sequence step

## [3.5.0] - 2024-06-16

### Added

- Text representation of sequence steps when exporting to mime type `text/plain`

## [3.4.0] - 2024-06-14

### Added

- Drag/drop for multiple parameter steps at once
- Copy, paste, cut for sequence steps (Ctrl+C, Ctrl+V, Ctrl+X)
- Select all steps shortcut (Ctrl+A)
