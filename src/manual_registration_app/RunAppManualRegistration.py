import argparse

from manual_registration_app.AppManualRegistration import call_app

def main():

    parser = argparse.ArgumentParser(description="")
    parser.add_argument("registration_files_list", type=str)
    parser.add_argument("upload_name", type=str)
    parser.add_argument("registration_dir", type=str)
    parser.add_argument("--resampled_image_dir", type=str, default=None)
    parser.add_argument("--resampled_mask_dir", type=str, default=None)
    args = parser.parse_args()

    call_app(
        args.registration_files_list,
        args.upload_name,
        args.registration_dir,
        args.resampled_image_dir,
        args.resampled_mask_dir
    )

if __name__ == "__main__":
    main()