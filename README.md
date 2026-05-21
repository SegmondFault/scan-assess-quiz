# scan-assess-quiz

Broken down into sections, depending on code base:

## Python
Simple Web App
- automatically detects and imports modules in the `modules` folder
- runs the discovered modules to generate questiosn in the `output` folder
- serves a simple web page to display the generated questions
- generates a report in the `reports` folder with the results of the quiz

Information on how modules are structured and how to create new ones can be found in `src/runners/README.md` and example modules can be found in the `modules` folder.

### Prerequisites

- Python 3.12+
- `nmap` installed and available on your `PATH` for the `count_devices` module.

### Run

```bash
python3 main.py
```

You can enter a custom target network/range (for example `192.168.1.0/24`) or press Enter to use the default.


## Java
Works using Springboot and Vaadin, creates a simple website, that uses localhost:8080 for asking the user some questions, populated by the Python call to get the information installed on the device.

Questions are stored in the questions folder as JSON entries 
### Prerequisites
Java 25
Maven tool, for building project and adding dependencies

### Run

```maven
mvn clean install
```

on QuizSelectorGame
And then run QuizSelectorGameApplication
Will be compiled into a WAR later

