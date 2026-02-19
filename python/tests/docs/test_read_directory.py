from d2cms.docs import read_directory


class TestReadDirectory:
    def test_empty_directory_returns_empty_lists(self, tmp_path):
        files, dirs = read_directory(tmp_path)
        assert files == []
        assert dirs == []

    def test_returns_files_separately_from_directories(self, tmp_path):
        (tmp_path / "doc.md").write_text("content")
        (tmp_path / "subdir").mkdir()
        files, dirs = read_directory(tmp_path)
        assert len(files) == 1
        assert len(dirs) == 1
        assert files[0].name == "doc.md"
        assert dirs[0].name == "subdir"

    def test_only_files(self, tmp_path):
        (tmp_path / "a.md").write_text("")
        (tmp_path / "b.md").write_text("")
        files, dirs = read_directory(tmp_path)
        assert len(files) == 2
        assert dirs == []

    def test_only_directories(self, tmp_path):
        (tmp_path / "child1").mkdir()
        (tmp_path / "child2").mkdir()
        files, dirs = read_directory(tmp_path)
        assert files == []
        assert len(dirs) == 2

    def test_does_not_recurse(self, tmp_path):
        subdir = tmp_path / "sub"
        subdir.mkdir()
        (subdir / "nested.md").write_text("")
        files, dirs = read_directory(tmp_path)
        assert files == []
        assert len(dirs) == 1
