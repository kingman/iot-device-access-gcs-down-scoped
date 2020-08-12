provider "google" {}

resource "google_project_service" "cloud-iot-apis" {
  project = var.google_project_id
  service = "cloudiot.googleapis.com"

  disable_dependent_services = true
  disable_on_destroy         = true
}

resource "google_project_service" "pubsub-apis" {
  project = var.google_project_id
  service = "pubsub.googleapis.com"

  disable_dependent_services = true
  disable_on_destroy         = true
}

resource "google_project_service" "functions-apis" {
  project = var.google_project_id
  service = "cloudfunctions.googleapis.com"

  disable_dependent_services = true
  disable_on_destroy         = true
}

resource "google_pubsub_topic" "default-telemetry" {
  name    = "default-telemetry"
  project = var.google_project_id

  depends_on = [
    google_project_service.pubsub-apis
  ]
}

resource "google_cloudiot_registry" "device-registry" {
  name    = var.google_iot_registry_id
  project = var.google_project_id
  region = var.google_default_region

  depends_on = [
    google_project_service.cloud-iot-apis,
    google_pubsub_topic.default-telemetry
  ]

  event_notification_configs {
    pubsub_topic_name = google_pubsub_topic.default-telemetry.id
  }

  http_config = {
    http_enabled_state = "HTTP_ENABLED"
  }

  mqtt_config = {
    mqtt_enabled_state = "MQTT_ENABLED"
  }
}

resource "google_cloudiot_device" "test-device" {
  name     = var.google_iot_device_id
  registry = google_cloudiot_registry.device-registry.id

  depends_on = [
      google_cloudiot_registry.device-registry
  ]

  credentials {
    public_key {
        format = "RSA_PEM"
        key = file(var.google_iot_device_key_path)
    }
  }
}

resource "google_service_account" "storage-reader-sa" {
  account_id   = "iot-storage-reader"
  display_name = "IoT Download"
}

resource "google_service_account" "storage-writer-sa" {
  account_id   = "iot-storage-writer"
  display_name = "IoT Upload"
}

resource "google_service_account" "token-broker-sa" {
  account_id   = "iot-token-broker"
  display_name = "Access Token Broker"
}

resource "google_project_iam_member" "storage-read-permission" {
  project = var.google_project_id
  role    = "roles/storage.objectViewer"
  member  = "serviceAccount:${google_service_account.storage-reader-sa.email}"
}

resource "google_project_iam_member" "storage-write-permission" {
  project = var.google_project_id
  role    = "roles/storage.objectCreator"
  member  = "serviceAccount:${google_service_account.storage-writer-sa.email}"
}

resource "google_service_account_iam_binding" "create-read-token-permission" {
  service_account_id = "projects/-/serviceAccounts/${google_service_account.storage-reader-sa.email}"
  role               = "roles/iam.serviceAccountTokenCreator"
  members = [
      "serviceAccount:${google_service_account.token-broker-sa.email}",
  ]
}

resource "google_service_account_iam_binding" "create-write-token-permission" {
  service_account_id = "projects/-/serviceAccounts/${google_service_account.storage-writer-sa.email}"
  role               = "roles/iam.serviceAccountTokenCreator"
  members = [
      "serviceAccount:${google_service_account.token-broker-sa.email}",
  ]
}

data "archive_file" "token-broker-source" {
  type        = "zip"
  output_path = "../functions/token-broker-source.zip"
  source_dir = "../functions/token-broker" 
}

resource "google_storage_bucket" "cf-source-bucket" {
  name = "cf-source-bucket-${var.google_project_id}"
}

resource "google_storage_bucket_object" "token-broker-archive" {
  name   = "token-broker-source.zip"
  bucket = google_storage_bucket.cf-source-bucket.name
  source = "../functions/token-broker-source.zip"
}

resource "google_cloudfunctions_function" "token-broker-cf" {
  name        = "token-broker"
  region      = var.google_default_region
  runtime     = "python38"

  available_memory_mb   = 256
  source_archive_bucket = google_storage_bucket.cf-source-bucket.name
  source_archive_object = google_storage_bucket_object.token-broker-archive.name
  trigger_http          = true
  timeout               = 60
  entry_point           = "generate_down_scoped_token"
  service_account_email =  google_service_account.token-broker-sa.email

  environment_variables = {
    TOKEN_LIFETIME = "1800"
    WRITE_SA = "${google_service_account.storage-writer-sa.email}"
    READ_SA = "${google_service_account.storage-reader-sa.email}"
  }
}