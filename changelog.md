# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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
- Export `FormDeviceConfigurationEditor` in `caqtus.gui.condetrol.device_configuration_editors`

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
