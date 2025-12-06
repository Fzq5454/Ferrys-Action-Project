# FAP Language

FAP (Ferry's Action Project) is a simple yet powerful programming language designed for beginners and educational purposes. With its clean syntax and intuitive structure, FAP makes programming accessible to everyone.

## Features

- **Simple Syntax**: Easy to learn with minimal keywords
- **Type Safety**: Strong typing with int, float, and str types
- **Powerful Features**: Functions, loops, conditionals, and more

## To Use

**Windows Users**:

### Step 1: Download

Step-by-Step Installation:
- Visit the FAP GitHub repository
- Go to Releases Page
- Click on the "Releases" section
- Find the version you need (latest recommended)
- Download the File
- Look for: FAP-<version>-Win.zip
- Example: FAP-1.5.1-Win.zip
- Click to download the file

### Step 2: Install

Step-by-Step Installation:
- Download: FAP-<version>-Win.zip
- Extract to: FAP-<version>-Win
- Open PowerShell in: C:\Users\YourName\Desktop\FAP-<version>-Win
- Run:
```
> powershell
Get-Content ".\&fapSetup.txt" | Invoke-Expression
```
- Wait for:
```
> powershell
[OK] Installation complete!
```

### Step 3: Write Your First Program

Create a new file called `hello.fap`:
```
> fap
@None My First FAP Program
out.Info("Hello, World!")
```

### Step 4: Run Your Program

Step-by-Step Execution:
- Open Terminal/PowerShell (Press Win + R, type powershell or cmd, or use Windows Terminal/Command Prompt)
- Run Your FAP Program
```
> powershell
fap run hello.fap
```
- Wait for Execution Results

***That's all STEP!***

## To Uninstall

**Windows Users**:

- Find the ``uninstall-fap.bat``
- Run ``uninstall-fap.bat``
- Type 'Y' to confirm
- Wait for:
```
> batch
Process completed.
```
