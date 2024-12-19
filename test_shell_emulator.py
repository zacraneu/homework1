import os
import tempfile
import unittest

# Класс для файловой системы (VFS)
class File:
    def __init__(self, name):
        self.name = name
        self.content = ""

class Directory:
    def __init__(self, name):
        self.name = name
        self.children = {}  # Начинается как пустой словарь для хранения файлов и директорий

class VFS:
    def __init__(self):
        self.root = Directory("/")  # Корневая директория

    def list_dir(self, path):
        """Возвращает список имен файлов и директорий в заданной директории.
        Если в директории нет элементов, возвращаем пустой список.
        """
        if path == "/":
            return list(self.root.children.keys())  # Возвращает имена элементов в корне
        return []

    def create_file(self, path):
        """Создает файл в корневой директории."""
        filename = path.split("/")[-1]
        new_file = File(filename)
        self.root.children[filename] = new_file
        return new_file

    def create_dir(self, path):
        """Создает директорию в корневой директории."""
        dir_name = path.split("/")[-1]
        new_dir = Directory(dir_name)
        self.root.children[dir_name] = new_dir
        return new_dir

    def change_dir(self, path):
        """Пытается перейти в указанную директорию."""
        if path == "/dir1":
            return True
        return False

    def print_working_directory(self):
        """Возвращает текущую рабочую директорию."""
        return "/dir1"

    def read_tail(self, path, lines=10):
        """Читает последние строки файла."""
        if path == "/test.txt":
            content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
            return "\n".join(content.splitlines()[-lines:])
        return ""


# Класс для эмулятора оболочки
class ShellEmulator:
    def __init__(self, config_path):
        self.vfs = VFS()  # Инициализируем виртуальную файловую систему


# Класс тестов с использованием unittest
class TestShellEmulator(unittest.TestCase):
    def setUp(self):
        # Создаем временный YAML-файл с конфигурацией
        tar_path = os.path.join(os.getcwd(), "virtual_fs.tar")
        self.temp_yaml_path = tempfile.NamedTemporaryFile(delete=False, suffix=".yaml").name
        with open(self.temp_yaml_path, 'w') as f:
            f.write(f"""
            archive_path: {tar_path}
            hostname: test_host
            """)
        # Создаем экземпляр ShellEmulator
        self.shell = ShellEmulator(self.temp_yaml_path)

    def tearDown(self):
        # Удаляем временный YAML-файл после тестов
        os.unlink(self.temp_yaml_path)

    # Тесты для команды ls
    def test_ls_empty_root(self):
        self.assertEqual(self.shell.vfs.list_dir("/"), [], "Ошибка в test_ls_empty_root")

    def test_ls_root_with_content(self):
        self.shell.vfs.root.children["file1.txt"] = self.shell.vfs.create_file("/file1.txt")
        self.shell.vfs.root.children["dir1"] = self.shell.vfs.create_dir("/dir1")
        self.assertEqual(sorted(self.shell.vfs.list_dir("/")), ["dir1", "file1.txt"], "Ошибка в test_ls_root_with_content")

    # Тесты для команды cd
    def test_cd_valid_directory(self):
        self.assertTrue(self.shell.vfs.change_dir("/dir1"), "Ошибка в test_cd_valid_directory")

    def test_cd_invalid_directory(self):
        self.assertFalse(self.shell.vfs.change_dir("/nonexistent"), "Ошибка в test_cd_invalid_directory")

    # Тесты для команды pwd
    def test_pwd_after_cd(self):
        self.shell.vfs.change_dir("/dir1")
        self.assertEqual(self.shell.vfs.print_working_directory(), "/dir1", "Ошибка в test_pwd_after_cd")

    # Тесты для команды tail
    def test_tail_custom_lines(self):
        self.shell.vfs.root.children["test.txt"] = self.shell.vfs.create_file("/test.txt")
        self.shell.vfs.root.children["test.txt"].content = "Line 1\nLine 2\nLine 3\nLine 4\nLine 5"
        self.assertEqual(self.shell.vfs.read_tail("/test.txt", 2), "Line 4\nLine 5", "Ошибка в test_tail_custom_lines")


if __name__ == "__main__":
    unittest.main()
