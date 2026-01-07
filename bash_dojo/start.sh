#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
BOLD='\033[1m'
NC='\033[0m' # No Color

DOJO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROGRESS_FILE="$DOJO_DIR/.progress"
PLAYGROUND="$DOJO_DIR/playground"

# Initialize progress
init_progress() {
    if [[ ! -f "$PROGRESS_FILE" ]]; then
        echo "current_mission=1" > "$PROGRESS_FILE"
        echo "completed_missions=" >> "$PROGRESS_FILE"
    fi
    source "$PROGRESS_FILE"
}

save_progress() {
    echo "current_mission=$current_mission" > "$PROGRESS_FILE"
    echo "completed_missions=$completed_missions" >> "$PROGRESS_FILE"
}

# Setup playground
setup_playground() {
    rm -rf "$PLAYGROUND"
    mkdir -p "$PLAYGROUND"
    cd "$PLAYGROUND"
}

print_banner() {
    clear
    echo -e "${CYAN}"
    echo "  ____            _       ____        _       "
    echo " | __ )  __ _ ___| |__   |  _ \  ___ (_) ___  "
    echo " |  _ \ / _\` / __| '_ \  | | | |/ _ \| |/ _ \ "
    echo " | |_) | (_| \__ \ | | | | |_| | (_) | | (_) |"
    echo " |____/ \__,_|___/_| |_| |____/ \___// |\___/ "
    echo "                                   |__/       "
    echo -e "${NC}"
    echo -e "${YELLOW}Learn bash through practice. Become the terminal master.${NC}"
    echo ""
}

print_mission_header() {
    local num=$1
    local title=$2
    echo -e "\n${BOLD}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${GREEN}  MISSION $num: $title${NC}"
    echo -e "${BOLD}═══════════════════════════════════════════════════════════${NC}\n"
}

# Mission definitions
mission_1() {
    print_mission_header 1 "First Steps - Where Am I?"
    setup_playground

    echo -e "${CYAN}LESSON:${NC} The 'pwd' command shows your current directory."
    echo -e "        The 'ls' command lists files in a directory.\n"

    echo -e "${YELLOW}CHALLENGE:${NC}"
    echo "  1. Use 'pwd' to see where you are"
    echo "  2. Use 'ls' to see what's in the dojo directory"
    echo ""
    echo -e "${BLUE}QUESTION:${NC} What command shows your current working directory?"
    echo -e "Type your answer (just the command name):"

    read -r answer
    if [[ "$answer" == "pwd" ]]; then
        echo -e "\n${GREEN}✓ Correct!${NC} 'pwd' = Print Working Directory"
        echo -e "\n${CYAN}TRY IT NOW:${NC} Type 'pwd' and press Enter"
        read -r cmd
        if [[ "$cmd" == "pwd" ]]; then
            eval "$cmd"
            echo -e "\n${GREEN}✓ Mission Complete!${NC}"
            return 0
        fi
    else
        echo -e "\n${RED}✗ Not quite.${NC} Hint: It stands for 'print working directory'"
        return 1
    fi
}

mission_2() {
    print_mission_header 2 "Navigation - The cd Command"
    setup_playground
    mkdir -p secret_folder/hidden_room
    echo "You found me!" > secret_folder/hidden_room/treasure.txt

    echo -e "${CYAN}LESSON:${NC} The 'cd' command changes directories."
    echo -e "        cd ..     = go up one level"
    echo -e "        cd folder = enter a folder"
    echo -e "        cd ~      = go to home directory\n"

    echo -e "${YELLOW}SETUP:${NC} I've created: playground/secret_folder/hidden_room/treasure.txt\n"

    echo -e "${BLUE}CHALLENGE:${NC} Navigate to hidden_room and read the treasure!"
    echo -e "Commands you'll need: cd, ls, cat\n"

    echo "You're now in the playground. Enter commands (type 'done' when finished):"
    cd "$PLAYGROUND"

    while true; do
        echo -ne "${GREEN}dojo>${NC} "
        read -r cmd

        if [[ "$cmd" == "done" ]]; then
            break
        elif [[ "$cmd" == "hint" ]]; then
            echo -e "${YELLOW}Hint: cd secret_folder, then cd hidden_room, then cat treasure.txt${NC}"
        elif [[ -n "$cmd" ]]; then
            eval "$cmd" 2>&1
        fi
    done

    echo -e "\n${CYAN}QUESTION:${NC} What does 'cd ..' do?"
    echo "  a) Delete current folder"
    echo "  b) Go to home directory"
    echo "  c) Go up one directory level"

    read -r answer
    if [[ "$answer" == "c" ]]; then
        echo -e "\n${GREEN}✓ Mission Complete!${NC}"
        return 0
    else
        echo -e "\n${RED}✗ Try again!${NC} '..' means parent directory"
        return 1
    fi
}

mission_3() {
    print_mission_header 3 "Creation - mkdir and touch"
    setup_playground

    echo -e "${CYAN}LESSON:${NC}"
    echo "  mkdir folder_name  = create a directory"
    echo "  mkdir -p a/b/c     = create nested directories"
    echo "  touch file.txt     = create an empty file"
    echo ""

    echo -e "${YELLOW}CHALLENGE:${NC} Create this structure:"
    echo "  playground/"
    echo "  └── projects/"
    echo "      ├── web/"
    echo "      │   └── index.html"
    echo "      └── scripts/"
    echo "          └── run.sh"
    echo ""

    echo "Enter commands (type 'check' to verify, 'hint' for help):"
    cd "$PLAYGROUND"

    while true; do
        echo -ne "${GREEN}dojo>${NC} "
        read -r cmd

        if [[ "$cmd" == "check" ]]; then
            if [[ -d "projects/web" && -d "projects/scripts" && \
                  -f "projects/web/index.html" && -f "projects/scripts/run.sh" ]]; then
                echo -e "\n${GREEN}✓ Perfect! Structure created!${NC}"
                echo -e "\nBonus: Use 'tree' or 'find .' to view your work"
                echo -e "\n${GREEN}✓ Mission Complete!${NC}"
                return 0
            else
                echo -e "${RED}✗ Not quite right. Use 'find .' to see what you have.${NC}"
            fi
        elif [[ "$cmd" == "hint" ]]; then
            echo -e "${YELLOW}Hint: mkdir -p projects/web projects/scripts${NC}"
            echo -e "${YELLOW}      touch projects/web/index.html projects/scripts/run.sh${NC}"
        elif [[ "$cmd" == "done" ]]; then
            return 1
        elif [[ -n "$cmd" ]]; then
            eval "$cmd" 2>&1
        fi
    done
}

mission_4() {
    print_mission_header 4 "Text Power - echo and redirection"
    setup_playground

    echo -e "${CYAN}LESSON:${NC}"
    echo "  echo 'text'          = print text"
    echo "  echo 'text' > file   = write to file (overwrites)"
    echo "  echo 'text' >> file  = append to file"
    echo "  cat file             = display file contents"
    echo ""

    echo -e "${YELLOW}CHALLENGE:${NC}"
    echo "  1. Create a file called 'todo.txt'"
    echo "  2. Add three tasks to it (one per line)"
    echo "  3. Display the contents"
    echo ""

    echo "Enter commands (type 'check' to verify):"
    cd "$PLAYGROUND"

    while true; do
        echo -ne "${GREEN}dojo>${NC} "
        read -r cmd

        if [[ "$cmd" == "check" ]]; then
            if [[ -f "todo.txt" ]]; then
                lines=$(wc -l < todo.txt)
                if [[ $lines -ge 3 ]]; then
                    echo -e "\n${GREEN}✓ Excellent! Your todo list:${NC}"
                    cat todo.txt
                    echo -e "\n${GREEN}✓ Mission Complete!${NC}"
                    return 0
                else
                    echo -e "${RED}✗ Need at least 3 lines. You have $lines.${NC}"
                fi
            else
                echo -e "${RED}✗ todo.txt not found${NC}"
            fi
        elif [[ "$cmd" == "hint" ]]; then
            echo -e "${YELLOW}Hint: echo 'Task 1' > todo.txt${NC}"
            echo -e "${YELLOW}      echo 'Task 2' >> todo.txt${NC}"
        elif [[ "$cmd" == "done" ]]; then
            return 1
        elif [[ -n "$cmd" ]]; then
            eval "$cmd" 2>&1
        fi
    done
}

mission_5() {
    print_mission_header 5 "The Pipe - Connecting Commands"
    setup_playground

    # Create sample data
    cat > names.txt << 'EOF'
Alice Johnson
Bob Smith
Charlie Brown
Alice Cooper
David Lee
Bob Dylan
Alice Walker
Eve Wilson
EOF

    echo -e "${CYAN}LESSON:${NC}"
    echo "  command1 | command2  = pipe output of cmd1 to cmd2"
    echo "  grep 'pattern' file  = search for pattern"
    echo "  wc -l                = count lines"
    echo "  sort                 = sort lines"
    echo "  uniq                 = remove duplicates"
    echo ""

    echo -e "${YELLOW}SETUP:${NC} I created 'names.txt' with some names.\n"
    echo "Contents:"
    cat names.txt
    echo ""

    echo -e "${BLUE}CHALLENGES:${NC}"
    echo "  1. Count how many lines contain 'Alice'"
    echo "  2. Sort the file alphabetically"
    echo "  3. Find all unique first names"
    echo ""

    echo -e "${CYAN}QUESTION:${NC} How many lines contain 'Alice'?"
    read -r answer

    correct=$(grep "Alice" names.txt | wc -l)
    if [[ "$answer" == "$correct" ]]; then
        echo -e "${GREEN}✓ Correct!${NC} The command: grep 'Alice' names.txt | wc -l"
        echo ""
        echo -e "${CYAN}QUESTION:${NC} What command sorts a file?"
        read -r answer
        if [[ "$answer" == "sort" ]]; then
            echo -e "\n${GREEN}✓ Mission Complete!${NC}"
            echo -e "\n${CYAN}PRO TIP:${NC} Try: cut -d' ' -f1 names.txt | sort | uniq"
            return 0
        fi
    fi

    echo -e "${RED}✗ Not quite.${NC} Hint: grep 'Alice' names.txt | wc -l"
    return 1
}

mission_6() {
    print_mission_header 6 "Find - The Search Master"
    setup_playground

    # Create complex structure
    mkdir -p src/{js,css,img} docs logs
    touch src/js/{app.js,utils.js,old.js.bak}
    touch src/css/{style.css,theme.css}
    touch src/img/{logo.png,banner.jpg}
    touch docs/{readme.md,api.md}
    touch logs/{error.log,access.log,debug.log}

    echo -e "${CYAN}LESSON:${NC}"
    echo "  find . -name '*.txt'       = find by name pattern"
    echo "  find . -type f             = find files only"
    echo "  find . -type d             = find directories only"
    echo "  find . -name '*.log' -delete  = find and delete"
    echo ""

    echo -e "${YELLOW}SETUP:${NC} I created a project structure.\n"
    find . -type f
    echo ""

    echo -e "${BLUE}CHALLENGES:${NC}"
    echo "  1. Find all .js files"
    echo "  2. Find all .log files"
    echo "  3. Count total files"
    echo ""

    echo "Enter commands (type 'quiz' when ready for questions):"
    cd "$PLAYGROUND"

    while true; do
        echo -ne "${GREEN}dojo>${NC} "
        read -r cmd

        if [[ "$cmd" == "quiz" ]]; then
            break
        elif [[ "$cmd" == "hint" ]]; then
            echo -e "${YELLOW}Hint: find . -name '*.js'${NC}"
        elif [[ -n "$cmd" ]]; then
            eval "$cmd" 2>&1
        fi
    done

    echo -e "\n${CYAN}QUESTION:${NC} How many .js files are there?"
    read -r answer

    correct=$(find . -name "*.js" | wc -l)
    if [[ "$answer" == "$correct" ]]; then
        echo -e "${GREEN}✓ Correct!${NC}"
        echo -e "\n${GREEN}✓ Mission Complete!${NC}"
        return 0
    else
        echo -e "${RED}✗ There are $correct .js files${NC}"
        return 1
    fi
}

mission_7() {
    print_mission_header 7 "Process Control - Background Jobs"
    setup_playground

    echo -e "${CYAN}LESSON:${NC}"
    echo "  command &            = run in background"
    echo "  jobs                 = list background jobs"
    echo "  ps                   = list processes"
    echo "  ps aux               = detailed process list"
    echo "  kill PID             = terminate process"
    echo "  Ctrl+C               = interrupt current process"
    echo "  Ctrl+Z               = suspend current process"
    echo "  bg                   = resume in background"
    echo "  fg                   = bring to foreground"
    echo ""

    echo -e "${YELLOW}CHALLENGE:${NC}"
    echo "  1. Run 'sleep 100 &' to start a background job"
    echo "  2. Use 'jobs' to see it"
    echo "  3. Use 'ps' to find its PID"
    echo "  4. Kill it with 'kill PID'"
    echo ""

    echo "Enter commands (type 'check' to verify job is killed):"

    while true; do
        echo -ne "${GREEN}dojo>${NC} "
        read -r cmd

        if [[ "$cmd" == "check" ]]; then
            sleep_jobs=$(jobs | grep -c sleep || true)
            if [[ $sleep_jobs -eq 0 ]]; then
                echo -e "\n${GREEN}✓ No sleep jobs running!${NC}"
                echo -e "\n${GREEN}✓ Mission Complete!${NC}"
                return 0
            else
                echo -e "${RED}✗ Sleep job still running. Kill it!${NC}"
            fi
        elif [[ "$cmd" == "hint" ]]; then
            echo -e "${YELLOW}Hint: jobs shows job numbers, ps shows PIDs${NC}"
            echo -e "${YELLOW}      Use 'kill %1' or 'kill <PID>'${NC}"
        elif [[ -n "$cmd" ]]; then
            eval "$cmd" 2>&1
        fi
    done
}

mission_8() {
    print_mission_header 8 "Permissions - chmod Mastery"
    setup_playground

    echo '#!/bin/bash
echo "Hello from script!"' > myscript.sh

    echo -e "${CYAN}LESSON:${NC}"
    echo "  ls -l               = show permissions"
    echo "  chmod +x file       = make executable"
    echo "  chmod 755 file      = rwxr-xr-x"
    echo "  chmod 644 file      = rw-r--r--"
    echo ""
    echo "  Permission numbers:"
    echo "    4 = read (r)"
    echo "    2 = write (w)"
    echo "    1 = execute (x)"
    echo "    7 = 4+2+1 = rwx"
    echo "    5 = 4+1   = r-x"
    echo ""

    echo -e "${YELLOW}SETUP:${NC} Created 'myscript.sh' - try running it!\n"
    echo "Contents:"
    cat myscript.sh
    echo ""

    echo -e "${BLUE}CHALLENGE:${NC}"
    echo "  1. Try './myscript.sh' (it will fail)"
    echo "  2. Check permissions with 'ls -l'"
    echo "  3. Make it executable"
    echo "  4. Run it successfully"
    echo ""

    echo "Enter commands (type 'check' when script runs):"
    cd "$PLAYGROUND"

    while true; do
        echo -ne "${GREEN}dojo>${NC} "
        read -r cmd

        if [[ "$cmd" == "check" ]]; then
            if [[ -x "myscript.sh" ]]; then
                echo -e "\n${GREEN}✓ Script is now executable!${NC}"
                ./myscript.sh
                echo -e "\n${GREEN}✓ Mission Complete!${NC}"
                return 0
            else
                echo -e "${RED}✗ Script not executable yet. Use chmod +x${NC}"
            fi
        elif [[ "$cmd" == "hint" ]]; then
            echo -e "${YELLOW}Hint: chmod +x myscript.sh${NC}"
        elif [[ -n "$cmd" ]]; then
            eval "$cmd" 2>&1
        fi
    done
}

mission_9() {
    print_mission_header 9 "Text Surgery - sed and awk"
    setup_playground

    cat > data.csv << 'EOF'
name,score,grade
Alice,95,A
Bob,82,B
Charlie,78,C
Diana,91,A
Eve,88,B
EOF

    echo -e "${CYAN}LESSON:${NC}"
    echo "  sed 's/old/new/' file      = replace first occurrence"
    echo "  sed 's/old/new/g' file     = replace all occurrences"
    echo "  sed -i 's/old/new/g' file  = edit file in place"
    echo "  awk '{print \$1}' file      = print first column"
    echo "  awk -F',' '{print \$2}'     = use comma delimiter"
    echo ""

    echo -e "${YELLOW}SETUP:${NC} Created 'data.csv':\n"
    cat data.csv
    echo ""

    echo -e "${BLUE}CHALLENGES:${NC}"
    echo "  1. Extract just the names (first column)"
    echo "  2. Extract just the scores (second column)"
    echo "  3. Replace 'Bob' with 'Robert'"
    echo ""

    echo "Enter commands (type 'quiz' when ready):"
    cd "$PLAYGROUND"

    while true; do
        echo -ne "${GREEN}dojo>${NC} "
        read -r cmd

        if [[ "$cmd" == "quiz" ]]; then
            break
        elif [[ "$cmd" == "hint" ]]; then
            echo -e "${YELLOW}Hint: awk -F',' '{print \$1}' data.csv${NC}"
            echo -e "${YELLOW}      sed 's/Bob/Robert/' data.csv${NC}"
        elif [[ -n "$cmd" ]]; then
            eval "$cmd" 2>&1
        fi
    done

    echo -e "\n${CYAN}QUESTION:${NC} What awk command prints the second column of a CSV?"
    echo "  a) awk '{print \$2}' file"
    echo "  b) awk -F',' '{print \$2}' file"
    echo "  c) awk -d',' '{print \$2}' file"

    read -r answer
    if [[ "$answer" == "b" ]]; then
        echo -e "\n${GREEN}✓ Correct! -F sets the field separator.${NC}"
        echo -e "\n${GREEN}✓ Mission Complete!${NC}"
        return 0
    else
        echo -e "\n${RED}✗ The answer is b. -F',' sets comma as delimiter.${NC}"
        return 1
    fi
}

mission_10() {
    print_mission_header 10 "Final Challenge - Real World Script"
    setup_playground

    # Create log files
    mkdir -p logs
    for i in {1..5}; do
        cat >> logs/app.log << EOF
2024-01-0$i 10:00:00 INFO Application started
2024-01-0$i 10:05:00 ERROR Database connection failed
2024-01-0$i 10:06:00 INFO Retrying connection
2024-01-0$i 10:07:00 INFO Database connected
2024-01-0$i 10:30:00 WARN Memory usage high
2024-01-0$i 11:00:00 ERROR Timeout on request
EOF
    done

    echo -e "${CYAN}FINAL BOSS: Log Analysis${NC}\n"
    echo "You have a log file at logs/app.log"
    echo ""
    echo -e "${YELLOW}TASKS:${NC}"
    echo "  1. Count total ERROR entries"
    echo "  2. Find unique error messages"
    echo "  3. Create a summary report"
    echo ""
    echo "Create a file called 'report.txt' containing:"
    echo "  - Total lines in log"
    echo "  - Number of ERRORs"
    echo "  - Number of WARNs"
    echo ""

    echo "Enter commands (type 'submit' to check your report):"
    cd "$PLAYGROUND"

    while true; do
        echo -ne "${GREEN}dojo>${NC} "
        read -r cmd

        if [[ "$cmd" == "submit" ]]; then
            if [[ -f "report.txt" ]]; then
                echo -e "\n${CYAN}Your report:${NC}"
                cat report.txt
                echo ""

                total=$(wc -l < logs/app.log)
                errors=$(grep -c "ERROR" logs/app.log)
                warns=$(grep -c "WARN" logs/app.log)

                if grep -q "$total\|$errors\|$warns" report.txt; then
                    echo -e "\n${GREEN}╔═══════════════════════════════════════╗${NC}"
                    echo -e "${GREEN}║     🎉 CONGRATULATIONS! 🎉            ║${NC}"
                    echo -e "${GREEN}║   You've completed the Bash Dojo!     ║${NC}"
                    echo -e "${GREEN}╚═══════════════════════════════════════╝${NC}"
                    echo ""
                    echo -e "${CYAN}Skills Mastered:${NC}"
                    echo "  ✓ Navigation (cd, pwd, ls)"
                    echo "  ✓ File operations (mkdir, touch, cp, mv, rm)"
                    echo "  ✓ Text manipulation (echo, cat, grep)"
                    echo "  ✓ Pipes and redirection"
                    echo "  ✓ Finding files (find, locate)"
                    echo "  ✓ Process management"
                    echo "  ✓ Permissions (chmod)"
                    echo "  ✓ Text processing (sed, awk)"
                    echo "  ✓ Log analysis"
                    echo ""
                    echo -e "${YELLOW}Next Steps:${NC}"
                    echo "  • Learn bash scripting (loops, conditions)"
                    echo "  • Explore xargs for bulk operations"
                    echo "  • Master regex patterns"
                    echo "  • Study cron for scheduling"
                    return 0
                fi
            fi
            echo -e "${RED}✗ Report incomplete. Include all three counts.${NC}"
        elif [[ "$cmd" == "hint" ]]; then
            echo -e "${YELLOW}Hint: wc -l logs/app.log${NC}"
            echo -e "${YELLOW}      grep -c 'ERROR' logs/app.log${NC}"
            echo -e "${YELLOW}      echo 'Total: X' > report.txt${NC}"
        elif [[ -n "$cmd" ]]; then
            eval "$cmd" 2>&1
        fi
    done
}

# Main menu
main_menu() {
    print_banner
    init_progress

    echo -e "${BOLD}MISSIONS:${NC}"
    echo "  1. First Steps - Where Am I?"
    echo "  2. Navigation - The cd Command"
    echo "  3. Creation - mkdir and touch"
    echo "  4. Text Power - echo and redirection"
    echo "  5. The Pipe - Connecting Commands"
    echo "  6. Find - The Search Master"
    echo "  7. Process Control - Background Jobs"
    echo "  8. Permissions - chmod Mastery"
    echo "  9. Text Surgery - sed and awk"
    echo "  10. Final Challenge - Real World Script"
    echo ""
    echo -e "  ${CYAN}c${NC}. Command cheatsheet"
    echo -e "  ${CYAN}q${NC}. Quit"
    echo ""
    echo -e "Current progress: Mission $current_mission"
    echo ""
    echo -n "Select mission (1-10): "
    read -r choice

    case $choice in
        1) mission_1 && ((current_mission=2)) ;;
        2) mission_2 && ((current_mission=3)) ;;
        3) mission_3 && ((current_mission=4)) ;;
        4) mission_4 && ((current_mission=5)) ;;
        5) mission_5 && ((current_mission=6)) ;;
        6) mission_6 && ((current_mission=7)) ;;
        7) mission_7 && ((current_mission=8)) ;;
        8) mission_8 && ((current_mission=9)) ;;
        9) mission_9 && ((current_mission=10)) ;;
        10) mission_10 ;;
        c|C) show_cheatsheet ;;
        q|Q) echo "Until next time, grasshopper."; exit 0 ;;
        *) echo "Invalid choice" ;;
    esac

    save_progress
    echo ""
    echo -n "Press Enter to continue..."
    read -r
    main_menu
}

show_cheatsheet() {
    clear
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo -e "${BOLD}            BASH COMMAND CHEATSHEET${NC}"
    echo -e "${CYAN}═══════════════════════════════════════════════════════════${NC}"
    echo ""
    echo -e "${YELLOW}NAVIGATION${NC}"
    echo "  pwd                  Print working directory"
    echo "  cd dir               Change to directory"
    echo "  cd ..                Go up one level"
    echo "  cd ~                 Go to home directory"
    echo "  ls                   List files"
    echo "  ls -la               List all with details"
    echo ""
    echo -e "${YELLOW}FILE OPERATIONS${NC}"
    echo "  touch file           Create empty file"
    echo "  mkdir dir            Create directory"
    echo "  mkdir -p a/b/c       Create nested directories"
    echo "  cp src dst           Copy file"
    echo "  mv src dst           Move/rename file"
    echo "  rm file              Remove file"
    echo "  rm -r dir            Remove directory"
    echo ""
    echo -e "${YELLOW}VIEWING FILES${NC}"
    echo "  cat file             Display file contents"
    echo "  less file            Page through file"
    echo "  head file            First 10 lines"
    echo "  tail file            Last 10 lines"
    echo "  tail -f file         Follow file updates"
    echo ""
    echo -e "${YELLOW}SEARCHING${NC}"
    echo "  grep pattern file    Search in file"
    echo "  grep -r pattern dir  Search recursively"
    echo "  find . -name '*.txt' Find files by name"
    echo "  find . -type f       Find files only"
    echo ""
    echo -e "${YELLOW}TEXT PROCESSING${NC}"
    echo "  sort file            Sort lines"
    echo "  uniq                 Remove duplicates"
    echo "  wc -l file           Count lines"
    echo "  cut -d',' -f1        Extract column"
    echo "  sed 's/a/b/g' file   Replace text"
    echo "  awk '{print \$1}'     Print first column"
    echo ""
    echo -e "${YELLOW}REDIRECTION${NC}"
    echo "  cmd > file           Output to file (overwrite)"
    echo "  cmd >> file          Append to file"
    echo "  cmd1 | cmd2          Pipe output"
    echo "  cmd 2>&1             Redirect stderr to stdout"
    echo ""
    echo -e "${YELLOW}PROCESSES${NC}"
    echo "  ps                   List processes"
    echo "  ps aux               Detailed process list"
    echo "  kill PID             Terminate process"
    echo "  cmd &                Run in background"
    echo "  jobs                 List background jobs"
    echo "  fg                   Bring to foreground"
    echo ""
    echo -e "${YELLOW}PERMISSIONS${NC}"
    echo "  chmod +x file        Make executable"
    echo "  chmod 755 file       rwxr-xr-x"
    echo "  chmod 644 file       rw-r--r--"
    echo "  chown user:group     Change ownership"
}

# Run
main_menu
