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
    google_project_service.pubsub-apis,
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
  account_id   = "iot-storage-reader-${var.google_project_id}"
  display_name = "IoT Download"
}

resource "google_service_account" "storage-writer-sa" {
  account_id   = "iot-storage-writer-${var.google_project_id}"
  display_name = "IoT Upload"
}

resource "google_service_account" "token-broker-sa" {
  account_id   = "token-broker-${var.google_project_id}"
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