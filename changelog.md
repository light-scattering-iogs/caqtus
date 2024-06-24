# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- HOWTO for creating device extension
- Function to get a copy of caqtus serialization converter

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
