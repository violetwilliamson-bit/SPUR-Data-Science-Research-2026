# VS Code Dev Container Installation

This guide explains how to install Docker Desktop and the VS Code Dev Containers extension on macOS, then open this project in its development container.

## 1. Install Git if needed

Open Terminal and check whether Git is already available:

```bash
git --version
```

If the command prints a Git version, continue to the next section. If macOS says that developer tools are required, install Apple's Command Line Tools:

```bash
xcode-select --install
```

Select **Install** in the macOS dialog, accept the license agreement, and wait for installation to finish. You do not need to install the full Xcode application. Verify Git afterward:

```bash
git --version
```

For more information, see Apple's [Command Line Tools installation instructions](https://developer.apple.com/documentation/xcode/installing-the-command-line-tools) and Git's [macOS installation options](https://git-scm.com/install/mac.html).

## 2. Install VS Code if needed

If Visual Studio Code is not already installed:

1. Open the official [Visual Studio Code download page](https://code.visualstudio.com/download).
2. Download the macOS build. The Universal build works on both Apple silicon and Intel Macs.
3. Open the downloaded `.dmg` file.
4. Drag **Visual Studio Code.app** into **Applications**.
5. Open VS Code from **Applications** or Spotlight.

Optionally enable the `code` Terminal command:

1. In VS Code, press `Cmd+Shift+P`.
2. Run **Shell Command: Install 'code' command in PATH**.
3. Restart Terminal.
4. Verify the command:

```bash
code --version
```

See the official [VS Code installation guide for macOS](https://code.visualstudio.com/docs/setup/mac) for more details.

## 3. Check which Mac processor you have

Open **Apple menu → About This Mac** and look for one of the following:

- **Chip: Apple M1/M2/M3/M4/M5** — choose the Apple silicon download.
- **Processor: Intel** — choose the Intel download.

## 4. Install Docker Desktop

1. Open the official [Docker Desktop for Mac installation page](https://docs.docker.com/desktop/setup/install/mac-install/).
2. Download the version matching your processor.
3. Open the downloaded `Docker.dmg` file.
4. Drag **Docker** into **Applications**.
5. Open **Applications → Docker**.
6. Accept the license agreement.
7. Choose **Use recommended settings**.
8. Enter your Mac password if prompted.
9. Wait until Docker reports that its engine is running. You should see the Docker whale icon in the macOS menu bar.

Docker Desktop may offer a sign-in screen, but a Docker account usually is not required to run local containers.

Verify the installation by opening Terminal and running:

```bash
docker --version
docker run --rm hello-world
```

The second command downloads and runs a small test container.

## 5. Install the VS Code Dev Containers extension

1. Open VS Code.
2. Open Extensions with `Cmd+Shift+X`.
3. Search for **Dev Containers**.
4. Select the extension published by **Microsoft**.
5. Confirm that its identifier is `ms-vscode-remote.remote-containers`.
6. Click **Install**.

Alternatively, install it from Terminal:

```bash
code --install-extension ms-vscode-remote.remote-containers
```

The Terminal method only works if the VS Code `code` command is installed.

## 6. Open this project in the container

1. Make sure Docker Desktop is running.
2. Open the `ai-agentic-tools-template` repository in VS Code.
3. Press `Cmd+Shift+P`.
4. Run **Dev Containers: Reopen in Container**.
5. Wait while VS Code downloads the image and runs the setup commands. The first launch may take several minutes.

When initialization finishes, the lower-left corner of VS Code should indicate that you are connected to a Dev Container.

## 7. Verify the project setup

Open a new VS Code terminal and run:

```bash
ls -la .devcontainer configs .skillshare
skillshare --version
```

To rerun everything in a clean container later, open the Command Palette with `Cmd+Shift+P` and select **Dev Containers: Rebuild and Reopen in Container**.

For more information, see Microsoft's official [VS Code Dev Containers tutorial](https://code.visualstudio.com/docs/devcontainers/tutorial).
