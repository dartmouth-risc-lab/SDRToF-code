# SDR-ToF

## Overview

This repository provides two software implementations for SDR-based Time-of-Flight sensing using USRP hardware:

- **GNU Radio**: Interactive graphical interface for rapid prototyping
- **C++**: High-performance implementation with greater control and throughput

## Getting Started

Build instructions are available in their respective directories.

## C++ Implementation

The C++ software enables precise configuration of modulation/demodulation frequencies within USRP RF capabilities and photodiode bandwidth constraints.

**Output**: 
- Binary files containing IQ samples
- Metadata CSV files logging ethernet connection dropouts

## Data Analysis

Recorded `.bin` files can be processed offline using Python for custom signal processing and analysis.
