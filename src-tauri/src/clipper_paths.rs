use std::{io, path::{Path, PathBuf}};

/// Create the new default without moving or deleting an existing legacy library.
pub fn prepare_default_library(documents: &Path) -> io::Result<PathBuf> {
    let root = documents.join("super-sag");
    std::fs::create_dir_all(root.join("clippings"))?;
    Ok(root)
}

pub fn export_name(browser: &str) -> Option<&'static str> {
    match browser {
        "chrome" => Some("Super-SAG-Web-Clipper-Chrome-Edge.zip"),
        "safari" => Some("Super-SAG-Web-Clipper-Safari.dmg"),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    use std::{sync::atomic::{AtomicU64, Ordering}, time::{SystemTime, UNIX_EPOCH}};
    static SEQUENCE: AtomicU64 = AtomicU64::new(0);

    struct TempDirectory(PathBuf);
    impl TempDirectory {
        fn new() -> Self {
            let nonce = SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos();
            let sequence = SEQUENCE.fetch_add(1, Ordering::Relaxed);
            let path = std::env::temp_dir().join(format!("super-sag-clipper-test-{}-{nonce}-{sequence}", std::process::id()));
            std::fs::create_dir(&path).unwrap();
            Self(path)
        }
    }
    impl Drop for TempDirectory {
        fn drop(&mut self) { std::fs::remove_dir_all(&self.0).unwrap(); }
    }

    #[test]
    fn creates_the_default_library_without_changing_existing_files() {
        let temp = TempDirectory::new();
        let legacy = temp.0.join("sag-wiki/clippings");
        std::fs::create_dir_all(&legacy).unwrap();
        std::fs::write(legacy.join("old.md"), "old content").unwrap();
        let root = prepare_default_library(&temp.0).unwrap();
        assert_eq!(root, temp.0.join("super-sag"));
        assert!(root.join("clippings").is_dir());
        let note = root.join("clippings/existing.md");
        std::fs::write(&note, "keep").unwrap();
        prepare_default_library(&temp.0).unwrap();
        assert_eq!(std::fs::read_to_string(note).unwrap(), "keep");
        assert_eq!(std::fs::read_to_string(legacy.join("old.md")).unwrap(), "old content");
    }

    #[test]
    fn existing_file_at_default_root_causes_an_error_without_replacement() {
        let temp = TempDirectory::new();
        let file = temp.0.join("super-sag");
        std::fs::write(&file, "user file").unwrap();
        assert!(prepare_default_library(&temp.0).is_err());
        assert_eq!(std::fs::read_to_string(file).unwrap(), "user file");
    }

    #[test]
    fn suggested_export_names_are_branded() {
        assert_eq!(export_name("chrome"), Some("Super-SAG-Web-Clipper-Chrome-Edge.zip"));
        assert_eq!(export_name("safari"), Some("Super-SAG-Web-Clipper-Safari.dmg"));
        assert_eq!(export_name("other"), None);
    }
}
