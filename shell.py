import tarfile
import yaml
import sys
import posixpath
import os

class VirtualFile:
    def __init__(self, name, is_dir=False):
        self.name = name
        self.is_dir = is_dir
        self.children = {}
        self.content = ""

class VirtualFileSystem:
    def __init__(self, tar_path):
        self.root = VirtualFile("/", is_dir=True)
        self.current_path = "/"
        self.load_tar(tar_path)

    def load_tar(self, tar_path):
        if not tarfile.is_tarfile(tar_path):
            print(f"Tar archive {tar_path} does not exist or is not a valid tar file.")
            sys.exit(1)
        with tarfile.open(tar_path, 'r') as tar:
            for member in tar.getmembers():
                if member.name in ['.', './', '']:
                    continue
                path = '/' + member.name.strip('/')
                parts = path.split('/')

                if parts[-1] == '':
                    continue

                current = self.root
                for part in parts[1:-1]:
                    if part not in current.children:
                        current.children[part] = VirtualFile(part, is_dir=True)
                    current = current.children[part]
                if member.isdir():
                    current.children[parts[-1]] = VirtualFile(parts[-1], is_dir=True)
                else:
                    vf = VirtualFile(parts[-1], is_dir=False)
                    file_obj = tar.extractfile(member)
                    if file_obj:
                        try:
                            vf.content = file_obj.read().decode('utf-8')
                        except UnicodeDecodeError:
                            vf.content = ""
                    current.children[parts[-1]] = vf

    def get_node(self, path):
        if posixpath.isabs(path):
            path = path.lstrip('/')
            current = self.root
        else:
            current = self.get_node(self.current_path)
        
        if path == "":
            return current
        parts = path.split('/')
        for part in parts:
            if part == "..":
                if current == self.root:
                    continue
                parent = self.get_node(posixpath.dirname(self.current_path))
                current = parent if parent else self.root
            elif part == "." or part == "":
                continue
            else:
                current = current.children.get(part)
                if current is None:
                    return None
        return current

    def list_dir(self, path):
        node = self.get_node(path)
        if node and node.is_dir:
            return sorted(node.children.keys())
        return None

    def change_dir(self, path):
        node = self.get_node(path)
        if node and node.is_dir:
            if posixpath.isabs(path):
                self.current_path = posixpath.normpath(path)
            else:
                self.current_path = posixpath.normpath(posixpath.join(self.current_path, path))
            if not self.current_path.startswith('/'):
                self.current_path = '/' + self.current_path
            return True
        return False

    def print_working_directory(self):
        return self.current_path

    def read_tail(self, path, lines=10):
        node = self.get_node(path)
        if node and not node.is_dir:
            content_lines = node.content.splitlines()
            return '\n'.join(content_lines[-lines:])
        return None

class ShellEmulator:
    def __init__(self, config_path):
        self.load_config(config_path)
        self.vfs = VirtualFileSystem(self.config['archive_path'])
        self.hostname = self.config['hostname']
        self.startup_script = self.config.get('startup_script', None)
        self.commands = {
            'ls': self.cmd_ls,
            'cd': self.cmd_cd,
            'pwd': self.cmd_pwd,
            'exit': self.cmd_exit,
            'tail': self.cmd_tail
        }
        self.running = True

    def load_config(self, config_path):
        if not os.path.exists(config_path) or not os.path.isfile(config_path):
            print(f"Configuration file {config_path} does not exist.")
            sys.exit(1)
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)

    def run(self):
        if self.startup_script:
            self.execute_startup_script()

        while self.running:
            try:
                cmd_input = input(f"{self.hostname}:{self.vfs.current_path}$ ").strip()
                if not cmd_input:
                    continue
                parts = cmd_input.split()
                cmd = parts[0]
                args = parts[1:]
                if cmd in self.commands:
                    self.commands[cmd](args)
                else:
                    print(f"{cmd}: command not found")
            except (EOFError, KeyboardInterrupt):
                print()
                break

    def execute_startup_script(self):
        if not os.path.exists(self.startup_script) or not os.path.isfile(self.startup_script):
            print(f"Startup script {self.startup_script} does not exist.")
            return
        with open(self.startup_script, 'r') as f:
            for line in f:
                line = line.strip()
                if line:
                    parts = line.split()
                    cmd = parts[0]
                    args = parts[1:]
                    if cmd in self.commands:
                        self.commands[cmd](args)

    def cmd_ls(self, args):
        path = args[0] if args else "."
        listing = self.vfs.list_dir(path)
        if listing is not None:
            print('  '.join(listing))
        else:
            print(f"ls: cannot access '{path}': No such directory")

    def cmd_cd(self, args):
        if not args:
            print("cd: missing operand")
            return
        path = args[0]
        success = self.vfs.change_dir(path)
        if not success:
            print(f"cd: no such file or directory: {path}")

    def cmd_pwd(self, args):
        print(self.vfs.print_working_directory())

    def cmd_tail(self, args):
        if not args:
            print("tail: missing file operand")
            return
        
        file_path = args[0]
        num_lines = 10  # По умолчанию читаем 10 строк
        if len(args) > 1 and args[1].startswith('-'):
            try:
                num_lines = int(args[1][1:])
            except ValueError:
                print(f"tail: invalid number of lines: '{args[1]}'")
                return
        
        node = self.vfs.get_node(file_path)
        if not node or node.is_dir:
            print(f"tail: cannot open '{file_path}': No such file or directory")
            return
        
        # Разбиваем содержимое файла на строки и берём последние N строк
        lines = node.content.splitlines()
        tail_lines = lines[-num_lines:] if num_lines > 0 else lines
        print("\n".join(tail_lines))


    def cmd_exit(self, args):
        self.running = False

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python emulator.py <config.yaml>")
        sys.exit(1)
    config_path = sys.argv[1]
    emulator = ShellEmulator(config_path)
    emulator.run()
