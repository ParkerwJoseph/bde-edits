/**
 * IngestionUploadZone Component
 *
 * Drag-and-drop file upload zone for data ingestion.
 * Based on reference UI design.
 */

import { useState, useRef } from 'react';
import type { DragEvent, ChangeEvent } from 'react';
import { Upload } from 'lucide-react';
import { ALL_ALLOWED_EXTENSIONS, getExtension } from '../../utils/fileUtils';
import styles from '../../styles/components/ingestion/IngestionUploadZone.module.css';

export interface IngestionUploadZoneProps {
  onFilesSelected: (files: File[]) => void;
  disabled?: boolean;
}

export function IngestionUploadZone({ onFilesSelected, disabled = false }: IngestionUploadZoneProps) {
  const [isDragging, setIsDragging] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  const handleDragOver = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    if (!disabled) {
      setIsDragging(true);
    }
  };

  const handleDragLeave = (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);
  };

  const handleDrop = async (e: DragEvent<HTMLDivElement>) => {
    e.preventDefault();
    setIsDragging(false);

    if (disabled) return;

    const items = e.dataTransfer.items;
    const allFiles: File[] = [];

    const processEntry = async (entry: FileSystemEntry): Promise<void> => {
      if (entry.isFile) {
        const fileEntry = entry as FileSystemFileEntry;
        return new Promise((resolve) => {
          fileEntry.file((file) => {
            Object.defineProperty(file, 'webkitRelativePath', {
              value: entry.fullPath.substring(1),
              writable: false,
            });
            allFiles.push(file);
            resolve();
          });
        });
      } else if (entry.isDirectory) {
        const dirEntry = entry as FileSystemDirectoryEntry;
        const reader = dirEntry.createReader();
        return new Promise((resolve) => {
          const readEntries = () => {
            reader.readEntries(async (entries) => {
              if (entries.length === 0) {
                resolve();
              } else {
                await Promise.all(entries.map(processEntry));
                readEntries();
              }
            });
          };
          readEntries();
        });
      }
    };

    const promises: Promise<void>[] = [];
    for (let i = 0; i < items.length; i++) {
      const entry = items[i].webkitGetAsEntry();
      if (entry) {
        promises.push(processEntry(entry));
      }
    }

    await Promise.all(promises);
    filterAndSubmit(allFiles);
  };

  const handleFileSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      filterAndSubmit(Array.from(e.target.files));
    }
    if (fileInputRef.current) {
      fileInputRef.current.value = '';
    }
  };

  const handleFolderSelect = (e: ChangeEvent<HTMLInputElement>) => {
    if (e.target.files) {
      filterAndSubmit(Array.from(e.target.files));
    }
    if (folderInputRef.current) {
      folderInputRef.current.value = '';
    }
  };

  const handleClick = () => {
    if (!disabled) {
      fileInputRef.current?.click();
    }
  };

  const handleBrowseFiles = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!disabled) {
      fileInputRef.current?.click();
    }
  };

  const handleBrowseFolder = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (!disabled) {
      folderInputRef.current?.click();
    }
  };

  const filterAndSubmit = (files: File[]) => {
    const allowedFiles = files.filter((file) => {
      const ext = getExtension(file.name);
      return ALL_ALLOWED_EXTENSIONS.includes(ext);
    });

    if (allowedFiles.length > 0) {
      onFilesSelected(allowedFiles);
    }
  };

  return (
    <div
      className={`${styles.container} ${isDragging ? styles.dragging : ''} ${disabled ? styles.disabled : ''}`}
      onDragOver={handleDragOver}
      onDragLeave={handleDragLeave}
      onDrop={handleDrop}
      onClick={handleClick}
    >
      <div className={styles.iconWrapper}>
        <Upload className={styles.icon} size={32} />
      </div>

      <h3 className={styles.title}>Upload Documents</h3>

      <p className={styles.description}>
        Drag and drop files or folders here. Supports PDFs, spreadsheets, and text documents.
      </p>

      <div className={styles.browseButtons}>
        <button
          type="button"
          className={styles.browseButton}
          onClick={handleBrowseFiles}
          disabled={disabled}
        >
          Browse Files
        </button>
        <button
          type="button"
          className={styles.browseButton}
          onClick={handleBrowseFolder}
          disabled={disabled}
        >
          Browse Folder
        </button>
      </div>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept={ALL_ALLOWED_EXTENSIONS.join(',')}
        className={styles.hiddenInput}
        onChange={handleFileSelect}
      />
      <input
        ref={folderInputRef}
        type="file"
        multiple
        className={styles.hiddenInput}
        onChange={handleFolderSelect}
        {...({ webkitdirectory: '', directory: '' } as React.InputHTMLAttributes<HTMLInputElement>)}
      />
    </div>
  );
}

export default IngestionUploadZone;
